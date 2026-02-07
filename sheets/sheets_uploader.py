#!/usr/bin/env python3
"""
Enhanced Trustpilot Reporting to Google Sheets with Dashboard
- Raw data tabs per brand (archive/debugging)
- Master Index tab (aggregates all brands)
- Interactive Dashboard tab with dropdowns and charts
"""

import os
import sys
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from decimal import Decimal
import json

load_dotenv()

class DashboardSheetsUploader:
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Report")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS in .env")
        
        # Handle relative paths
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir) if 'sheets' in current_dir else current_dir
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
        # Setup credentials
        self.scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=self.scopes)
        self.gc = gspread.authorize(self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        
        print("✅ Authenticated with Google API")
    
    def find_master_sheet(self):
        """Find master spreadsheet"""
        print(f"  🔍 Searching for sheet: '{self.spreadsheet_name}'")
        print(f"  📁 In folder: {self.folder_id}")
        
        query = (
            f"'{self.folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.spreadsheet' and "
            f"name='{self.spreadsheet_name}' and "
            f"trashed=false"
        )
        
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print(f"  ❌ No sheets found matching query")
            raise FileNotFoundError(
                f"❌ Master sheet '{self.spreadsheet_name}' not found in folder.\n"
                f"   Create it at: https://drive.google.com/drive/folders/{self.folder_id}"
            )
        
        print(f"  ✅ Found sheet: {files[0]['name']} ({files[0]['id']})")
        return files[0]['id']
    
    def get_or_create_brand_tab(self, workbook, brand_name):
        """Get or create raw data tab for brand"""
        print(f"    🔍 Looking for tab: {brand_name}")
        try:
            ws = workbook.worksheet(brand_name)
            print(f"    ✅ Tab exists: {brand_name}")
            return ws
        except:
            print(f"    ➕ Creating new tab: {brand_name}")
            ws = workbook.add_worksheet(title=brand_name, rows=5000, cols=50)
            
            headers = [
                'iso_week', 'week_start', 'week_end', 
                'brand_name', 'business_id', 'website', 'logo_url', 'star_rating_svg',
                'trust_score', 'stars', 'total_reviews_all_time', 'is_claimed',
                'total_reviews', 'total_reviews_last_week', 'wow_change', 'wow_change_pct',
                'avg_rating', 'avg_rating_last_week', 'wow_rating_change',
                'positive_count', 'positive_pct', 'neutral_count', 'neutral_pct',
                'negative_count', 'negative_pct',
                'rating_5', 'rating_4', 'rating_3', 'rating_2', 'rating_1',
                'reviews_with_reply', 'reviews_without_reply', 'response_rate_pct', 
                'avg_response_hours', 'avg_response_days',
                'verified_count', 'organic_count', 'reviews_edited',
                'languages_json', 'top_countries',
                'top_negative_themes', 'top_positive_themes', 'top_neutral_themes',
                'categories', 'ai_summary', 'generated_at'
            ]
            
            print(f"    📝 Writing {len(headers)} column headers")
            ws.update(values=[headers], range_name='A1')
            ws.format('A1:AN1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            ws.freeze(rows=1)
            print(f"    ✅ Tab created and formatted")
            
            return ws
    
    def _ensure_master_index_columns(self, workbook, spreadsheet_id):
        """Ensure Master Index has enough columns and helper column U"""
        
        print("    🔍 Checking Master Index columns...")
        
        # Get sheet metadata
        sheet_metadata = self.sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        master_index_sheet_id = None
        current_cols = 0
        
        for sheet in sheet_metadata['sheets']:
            if sheet['properties']['title'] == 'Master Index':
                master_index_sheet_id = sheet['properties']['sheetId']
                current_cols = sheet['properties']['gridProperties']['columnCount']
                break
        
        if not master_index_sheet_id:
            return  # Will be created later
        
        # Expand if needed
        if current_cols < 30:
            print(f"    📏 Expanding Master Index from {current_cols} to 30 columns...")
            
            expand_request = {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': master_index_sheet_id,
                        'gridProperties': {
                            'columnCount': 30
                        }
                    },
                    'fields': 'gridProperties.columnCount'
                }
            }
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [expand_request]}
            ).execute()
            
            print(f"    ✅ Expanded to 30 columns")
        
        # Add helper column U if it doesn't exist
        print("    📝 Adding/updating helper column U...")
        
        master_index = workbook.worksheet('Master Index')
        
        # Add header
        master_index.update(values=[['lookup_key']], range_name='U1')
        
        # Get number of rows
        values = master_index.get_all_values()
        last_row = len(values)
        
        if last_row > 1:
            # Add formula to all rows
            formulas = [[f'=A{i}&"|"&B{i}'] for i in range(2, last_row + 1)]
            if formulas:
                master_index.update(values=formulas, range_name=f'U2:U{last_row}')
                print(f"    ✅ Helper column updated (U2:U{last_row})")
    
    def get_or_create_master_index(self, workbook, spreadsheet_id):
        """Get or create Master Index tab"""
        try:
            ws = workbook.worksheet("Master Index")
            print(f"    ✅ Master Index exists")
            
            # Ensure it has helper column
            self._ensure_master_index_columns(workbook, spreadsheet_id)
            
            return ws
        except:
            print(f"    ➕ Creating Master Index tab")
            ws = workbook.add_worksheet(title="Master Index", rows=10000, cols=30, index=0)
            
            headers = [
                'brand_name', 'iso_week', 'week_start', 'week_end',
                'logo_url', 'star_rating_svg', 'website',
                'total_reviews', 'wow_change', 'wow_change_pct',
                'avg_rating', 'wow_rating_change',
                'positive_count', 'positive_pct',
                'negative_count', 'negative_pct',
                'response_rate_pct', 'avg_response_hours',
                'trust_score', 'total_reviews_all_time', 'lookup_key'
            ]
            
            ws.update(values=[headers], range_name='A1')
            ws.format('A1:U1', {
                'textFormat': {'bold': True, 'fontSize': 11},
                'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            ws.freeze(rows=1)
            
            print(f"    ✅ Master Index created with 30 columns")
            
            return ws
    
    def get_or_create_dashboard(self, workbook, spreadsheet_id):
        """Get or create Dashboard tab"""
        try:
            ws = workbook.worksheet("Dashboard")
            print(f"    ✅ Dashboard exists")
            return ws
        except:
            print(f"    ➕ Creating Dashboard tab")
            ws = workbook.add_worksheet(title="Dashboard", rows=100, cols=26, index=0)
            
            # Setup dashboard structure
            self._setup_dashboard_layout(ws)
            
            print(f"    ✅ Dashboard created")
            
            return ws
    
    def _setup_dashboard_layout(self, ws):
        """Setup initial dashboard layout with formulas (European locale, lookup_key safe)"""

        # Helper to generate INDEX/MATCH formula
        def formula_lookup(col_letter, text=False):
            if text:
                return f'=IFERROR(INDEX(\'Master Index\'!{col_letter}:{col_letter}; MATCH(B3&"|"&B4; \'Master Index\'!U:U; 0)); "")'
            else:
                return f'=IFERROR(INDEX(\'Master Index\'!{col_letter}:{col_letter}; MATCH(B3&"|"&B4; \'Master Index\'!U:U; 0)); 0)'

        # Title
        ws.update(values=[['TRUSTPILOT BRAND DASHBOARD']], range_name='A1')
        ws.merge_cells('A1:Z1')
        ws.format('A1', {
            'textFormat': {'bold': True, 'fontSize': 18},
            'horizontalAlignment': 'CENTER',
            'backgroundColor': {'red': 0.2, 'green': 0.5, 'blue': 0.8},
            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })

        # Filters section
        ws.update(values=[['SELECT BRAND:']], range_name='A3')
        ws.update(values=[['SELECT WEEK:']], range_name='A4')
        ws.format('A3:A4', {'textFormat': {'bold': True}})

        # Placeholder text for dropdowns (will be replaced by data validation)
        ws.update(values=[['Select brand...']], range_name='B3')
        ws.update(values=[['Select week...']], range_name='B4')
        ws.format('B3:B4', {
            'backgroundColor': {'red': 1, 'green': 1, 'blue': 0.9},
            'horizontalAlignment': 'LEFT'
        })

        # Brand header section
        ws.update(values=[['BRAND PROFILE']], range_name='A6')
        ws.merge_cells('A6:F6')
        ws.format('A6', {
            'textFormat': {'bold': True, 'fontSize': 14},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

        # Brand metadata labels with formulas
        labels = [
            ['Brand Name:', formula_lookup('A', text=True)],
            ['Website:', formula_lookup('G', text=True)],
            ['Trust Score:', formula_lookup('S')],
            ['Total Reviews:', formula_lookup('T')],
        ]
        ws.update(values=labels, range_name='A7')
        ws.format('A7:A10', {'textFormat': {'bold': True}})

        # KPI / Weekly Metrics section
        ws.update(values=[['WEEKLY METRICS']], range_name='A12')
        ws.merge_cells('A12:Z12')
        ws.format('A12', {
            'textFormat': {'bold': True, 'fontSize': 14},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })

        # KPI cards structure
        kpi_cards = [
            ['Reviews This Week', 'Avg Rating', 'Positive %', 'Negative %', 'Response Rate', 'Avg Response'],
            [
                formula_lookup('H'),      # total_reviews
                formula_lookup('K'),      # avg_rating
                formula_lookup('N'),      # positive_pct
                formula_lookup('P'),      # negative_pct
                formula_lookup('Q'),      # response_rate_pct
                formula_lookup('R'),      # avg_response_hours
            ],
            [
                formula_lookup('I', text=True),  # wow_change
                formula_lookup('L'),             # wow_rating_change
                '', '', '', ''
            ]
        ]
        ws.update(values=kpi_cards, range_name='A13')

        # Format KPI headers
        ws.format('A13:F13', {
            'textFormat': {'bold': True, 'fontSize': 11},
            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8},
            'horizontalAlignment': 'CENTER'
        })

        # Format KPI values
        ws.format('A14:F14', {
            'textFormat': {'fontSize': 16, 'bold': True},
            'horizontalAlignment': 'CENTER',
            'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'}
        })

        # Format WoW changes / last row
        ws.format('A15:F15', {
            'textFormat': {'fontSize': 10, 'italic': True},
            'horizontalAlignment': 'CENTER'
        })

        # Placeholder sections for charts
        ws.update(values=[['SENTIMENT BREAKDOWN']], range_name='A17')
        ws.update(values=[['RATING DISTRIBUTION']], range_name='H17')
        ws.update(values=[['TOP COMPLAINTS']], range_name='A25')
        ws.update(values=[['TOP PRAISE']], range_name='H25')

        chart_titles = ['A17', 'H17', 'A25', 'H25']
        for cell in chart_titles:
            ws.format(cell, {
                'textFormat': {'bold': True, 'fontSize': 12},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })

        # Instructions section
        ws.update(values=[['INSTRUCTIONS:']], range_name='A35')
        ws.update(values=[['1. Select a brand from dropdown B3']], range_name='A36')
        ws.update(values=[['2. Select an ISO week from dropdown B4']], range_name='A37')
        ws.update(values=[['3. Dashboard updates automatically']], range_name='A38')
        ws.update(values=[['4. Manually add data validation to B3 (Master Index!A2:A) and B4 (Master Index!B2:B)']], range_name='A39')
        ws.format('A35', {'textFormat': {'bold': True}})
        ws.format('A36:A39', {'textFormat': {'italic': True}})
    
    def format_themes_list(self, themes):
        """Format themes array into readable string"""
        if not themes:
            return ""
        return ", ".join([f"{t['topic']} ({t['count']})" for t in themes[:5]])
    
    def safe_numeric(self, val):
        """Convert Decimal to float, handle None"""
        if val is None or val == '':
            return ''
        if isinstance(val, Decimal):
            return float(val)
        return val
    
    def upload_report(self, brand_name, report_data):
        """Upload report to all three layers: raw data, master index, dashboard"""
        
        print(f"\n{'='*70}")
        print(f"UPLOADING REPORT")
        print(f"{'='*70}\n")
        print(f"Brand: {brand_name}")
        print(f"Week: {report_data['report_metadata']['iso_week']}\n")
        
        # Get master sheet
        spreadsheet_id = self.find_master_sheet()
        workbook = self.gc.open_by_key(spreadsheet_id)
        
        # Extract data
        rm = report_data['report_metadata']
        c = report_data['company']
        rv = report_data['week_stats']['review_volume']
        rp = report_data['week_stats']['rating_performance']
        s = report_data['week_stats']['sentiment']
        rd = report_data['week_stats']['rating_distribution']
        resp = report_data['week_stats']['response_performance']
        ca = report_data['week_stats']['content_analysis']
        
        # LAYER 1: Update raw brand tab
        print("  📊 Layer 1: Raw data tab...")
        brand_ws = self.get_or_create_brand_tab(workbook, brand_name)
        
        raw_row = [
            rm['iso_week'], rm['week_start'], rm['week_end'], 
            c['brand_name'], c.get('business_id', ''), c.get('website', ''), 
            c.get('logo_url', ''), c.get('star_rating_svg', ''),
            self.safe_numeric(c.get('trust_score', '')),
            self.safe_numeric(c.get('stars', '')),
            self.safe_numeric(c.get('total_reviews_all_time', '')),
            c.get('is_claimed', ''),
            rv['total_this_week'], rv['total_last_week'], rv['wow_change'],
            self.safe_numeric(rv.get('wow_change_pct', '')),
            self.safe_numeric(rp['avg_rating_this_week']),
            self.safe_numeric(rp.get('avg_rating_last_week', '')),
            self.safe_numeric(rp.get('wow_change', '')),
            s['positive']['count'], self.safe_numeric(s['positive']['percentage']),
            s['neutral']['count'], self.safe_numeric(s['neutral']['percentage']),
            s['negative']['count'], self.safe_numeric(s['negative']['percentage']),
            rd['5_stars'], rd['4_stars'], rd['3_stars'], rd['2_stars'], rd['1_star'],
            resp['reviews_with_response'], resp.get('reviews_without_response', ''),
            self.safe_numeric(resp['response_rate_pct']),
            self.safe_numeric(resp.get('avg_response_time_hours', '')),
            self.safe_numeric(resp.get('avg_response_time_days', '')),
            rv['by_source']['verified_invited'], rv['by_source']['organic'],
            resp['reviews_edited'],
            json.dumps({k: int(v) if isinstance(v, int) else float(v) if isinstance(v, (Decimal, float)) else v 
                       for k, v in rv.get('by_language', {}).items()}),
            ', '.join([f"{country['country']} ({country['review_count']})" for country in rv.get('by_country', [])[:10]]),
            self.format_themes_list(ca['negative_themes']),
            self.format_themes_list(ca['positive_themes']),
            self.format_themes_list(ca.get('neutral_themes', [])),
            ', '.join([cat if isinstance(cat, str) else cat.get('name', str(cat)) for cat in c.get('categories', [])]),
            c.get('ai_summary', {}).get('summary_text', '')[:1000] if c.get('ai_summary') else '',
            rm['generated_at']
        ]
        
        print(f"    📝 Prepared row with {len(raw_row)} columns")
        
        # Define iso_week first
        iso_week = rm['iso_week']
        
        # Check if week exists
        print(f"    🔍 Checking if {iso_week} exists...")
        all_data = brand_ws.get_all_values()
        print(f"    📊 Found {len(all_data)} total rows (including header)")
        
        row_index = None
        
        for idx, row in enumerate(all_data[1:], start=2):
            if row and row[0] == iso_week:
                row_index = idx
                break
        
        if row_index:
            print(f"    ↻ Updating existing row {row_index} for {iso_week}")
            brand_ws.update(values=[raw_row], range_name=f'A{row_index}')
            print(f"    ✅ Row updated")
        else:
            print(f"    ➕ Appending new row for {iso_week}")
            brand_ws.append_row(raw_row)
            print(f"    ✅ Row appended")
        
        # LAYER 2: Update Master Index
        print("  📊 Layer 2: Master Index...")
        master_ws = self.get_or_create_master_index(workbook, spreadsheet_id)
        
        # Build lookup key
        lookup_key = f"{brand_name}|{iso_week}"
        
        index_row = [
            brand_name,
            rm['iso_week'],
            rm['week_start'],
            rm['week_end'],
            c.get('logo_url', ''),
            c.get('star_rating_svg', ''),
            c.get('website', ''),
            rv['total_this_week'],
            rv['wow_change'],
            self.safe_numeric(rv.get('wow_change_pct', '')),
            self.safe_numeric(rp['avg_rating_this_week']),
            self.safe_numeric(rp.get('wow_change', '')),
            s['positive']['count'],
            self.safe_numeric(s['positive']['percentage']),
            s['negative']['count'],
            self.safe_numeric(s['negative']['percentage']),
            self.safe_numeric(resp['response_rate_pct']),
            self.safe_numeric(resp.get('avg_response_time_hours', '')),
            self.safe_numeric(c.get('trust_score', '')),
            self.safe_numeric(c.get('total_reviews_all_time', '')),
            lookup_key  # Column U - helper for lookups
        ]
        
        print(f"    📝 Prepared Master Index row with {len(index_row)} columns")
        
        # Check if this brand+week combo exists in Master Index
        print(f"    🔍 Checking Master Index for {brand_name} {iso_week}")
        all_master = master_ws.get_all_values()
        print(f"    📊 Master Index has {len(all_master)} total rows")
        
        master_key = f"{brand_name}{iso_week}"
        master_row_index = None
        
        for idx, row in enumerate(all_master[1:], start=2):
            if row and len(row) >= 2 and f"{row[0]}{row[1]}" == master_key:
                master_row_index = idx
                print(f"    🎯 Found existing row at index {idx}")
                break
        
        if master_row_index:
            print(f"    ↻ Updating Master Index row {master_row_index}")
            master_ws.update(values=[index_row], range_name=f'A{master_row_index}')
            print(f"    ✅ Master Index updated")
        else:
            print(f"    ➕ Appending new row to Master Index")
            master_ws.append_row(index_row)
            print(f"    ✅ Master Index appended")
        
        # LAYER 3: Ensure Dashboard exists
        print("  📊 Layer 3: Dashboard...")
        dashboard_ws = self.get_or_create_dashboard(workbook, spreadsheet_id)
        print(f"    ✓ Dashboard ready")
        
        print(f"\n{'='*70}")
        print(f"✅ UPLOAD COMPLETE")
        print(f"{'='*70}")
        print(f"🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"📊 Use Dashboard tab for interactive reporting")
        print(f"\n💡 Manual step needed:")
        print(f"   - Add data validation to B3 (range: Master Index!A2:A)")
        print(f"   - Add data validation to B4 (range: Master Index!B2:B)\n")
        
        return spreadsheet_id


def main():
    """CLI entry point"""
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python sheets_uploader.py <brand_name> <report_json_file>")
        print("  python sheets_uploader.py <brand_name> <company_domain> <iso_week>")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    
    if sys.argv[2].endswith('.json'):
        report_file = sys.argv[2]
        
        if not os.path.exists(report_file):
            print(f"❌ Report file not found: {report_file}")
            sys.exit(1)
        
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
    
    else:
        if len(sys.argv) < 4:
            print("❌ Missing iso_week parameter")
            sys.exit(1)
        
        company_domain = sys.argv[2]
        iso_week = sys.argv[3]
        
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        from db import Database
        from generate_weekly_report import generate_weekly_report
        
        print(f"📊 Generating report from database...")
        db = Database()
        db.connect()
        report_data = generate_weekly_report(db, company_domain, iso_week)
        db.close()
        
        if not report_data:
            print(f"❌ Failed to generate report")
            sys.exit(1)
    
    uploader = DashboardSheetsUploader()
    uploader.upload_report(brand_name, report_data)


if __name__ == "__main__":
    main()