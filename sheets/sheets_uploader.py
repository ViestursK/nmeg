#!/usr/bin/env python3
"""
Google Sheets Uploader - Clean Mini-App Architecture
====================================================

Architecture:
1. ONE raw_data sheet (append-only, long format)
2. ONE dashboard sheet (interactive with selectors)
3. ONE definitions sheet (metric explanations)

Design Principles:
- Append-only (never overwrite history)
- Brand-agnostic (works for 1 or 100 brands)
- Dynamic KPIs (calculated in formulas, not stored)
- Interactive filtering (dropdown selectors)
"""

import os
from datetime import datetime
from decimal import Decimal
import json
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()


class SheetsUploader:
    """Clean, battle-tested Google Sheets uploader"""
    
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Dashboard")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS in .env")
        
        # Handle relative paths
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if os.path.basename(current_dir) == 'sheets':
                project_root = os.path.dirname(current_dir)
            else:
                project_root = current_dir
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
        # Setup credentials
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.gc = gspread.authorize(self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        
        print("✅ Google Sheets authenticated")
    
    def find_or_create_spreadsheet(self):
        """Find existing spreadsheet or create new one"""
        
        # Search for existing
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
        
        if files:
            print(f"✅ Found existing sheet: {files[0]['name']}")
            return files[0]['id']
        
        # Create new
        print(f"➕ Creating new spreadsheet: {self.spreadsheet_name}")
        spreadsheet = self.gc.create(self.spreadsheet_name, folder_id=self.folder_id)
        return spreadsheet.id
    
    def setup_raw_data_sheet(self, workbook):
        """Setup or verify raw_data sheet structure"""
        
        print("  📊 Setting up raw_data sheet...")
        
        try:
            ws = workbook.worksheet('raw_data')
            print("    ✅ Sheet exists")
        except:
            ws = workbook.add_worksheet(title='raw_data', rows=10000, cols=50)
            print("    ➕ Created new sheet")
        
        # Check if headers exist AND are complete (not just A1)
        try:
            existing_headers = ws.row_values(1)
            # We expect 60+ columns, so check if we have at least 10
            has_headers = len(existing_headers) >= 10
        except:
            has_headers = False
        
        if not has_headers:
            print("    📝 Writing headers...")
            headers = [
                # Identifiers
                'snapshot_date', 'iso_week', 'week_start', 'week_end',
                'brand_id', 'brand_name', 'website', 'business_id',
                
                # Company Info
                'trust_score', 'total_reviews_alltime', 'is_claimed', 'categories',
                'logo_url', 'star_rating_svg',
                
                # Review Volume
                'reviews_this_week', 'reviews_last_week', 'wow_change', 'wow_change_pct',
                
                # Rating Performance
                'avg_rating', 'avg_rating_last_week', 'rating_wow_change',
                
                # Sentiment
                'positive_count', 'positive_pct',
                'neutral_count', 'neutral_pct',
                'negative_count', 'negative_pct',
                
                # Rating Distribution
                'rating_5_star', 'rating_4_star', 'rating_3_star', 'rating_2_star', 'rating_1_star',
                
                # Response Performance
                'reviews_with_reply', 'response_rate_pct', 'avg_response_hours', 'avg_response_days',
                
                # Sources
                'verified_count', 'organic_count',
                
                # Languages & Countries (top 3)
                'top_language_1', 'top_language_1_count',
                'top_language_2', 'top_language_2_count',
                'top_language_3', 'top_language_3_count',
                'top_country_1', 'top_country_1_count',
                'top_country_2', 'top_country_2_count',
                'top_country_3', 'top_country_3_count',
                
                # Content Analysis (top 5 each)
                'positive_theme_1', 'positive_theme_1_count',
                'positive_theme_2', 'positive_theme_2_count',
                'positive_theme_3', 'positive_theme_3_count',
                'negative_theme_1', 'negative_theme_1_count',
                'negative_theme_2', 'negative_theme_2_count',
                'negative_theme_3', 'negative_theme_3_count',
                
                # AI Summary
                'ai_summary',
                
                # Metadata
                'generated_at'
            ]
            
            ws.update('A1', [headers])
            
            # Format header row
            ws.format('A1:BZ1', {
                'textFormat': {'bold': True, 'fontSize': 10},
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            
            ws.freeze(rows=1)
            print("    ✅ Headers configured")
        
        return ws
    
    def setup_dashboard_sheet(self, workbook, spreadsheet_id):
        """Setup interactive dashboard with selectors and KPIs"""
        
        print("  📈 Setting up dashboard sheet...")
        
        try:
            ws = workbook.worksheet('dashboard')
            print("    ✅ Sheet exists")
        except:
            ws = workbook.add_worksheet(title='dashboard', rows=100, cols=20)
            print("    ➕ Created new sheet")
        
        # ========================================
        # SELECTORS SECTION (Rows 1-5)
        # ========================================
        
        ws.update('A1', [['TRUSTPILOT DASHBOARD']])
        ws.merge_cells('A1:D1')
        ws.format('A1', {
            'textFormat': {'bold': True, 'fontSize': 18},
            'horizontalAlignment': 'CENTER',
            'backgroundColor': {'red': 0.1, 'green': 0.1, 'blue': 0.1},
            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })
        
        # Selector labels
        ws.update('A3', [['Select Brand:']])
        ws.update('A4', [['Select Week:']])
        ws.format('A3:A4', {'textFormat': {'bold': True, 'fontSize': 11}})
        
        # Placeholder cells (these will have data validation)
        ws.update('B3', [['[Add data validation: raw_data unique brands]']])
        ws.update('B4', [['[Add data validation: raw_data unique weeks]']])
        ws.format('B3:B4', {
            'backgroundColor': {'red': 1, 'green': 1, 'blue': 0.8},
            'horizontalAlignment': 'LEFT'
        })
        
        # Instructions
        ws.update('E3', [['Instructions:']])
        ws.update('E4', [['1. Use Data > Data validation on B3 to add brand dropdown']])
        ws.update('E5', [['2. Use Data > Data validation on B4 to add week dropdown']])
        ws.update('E6', [['3. Dashboard auto-updates when you change selections']])
        ws.format('E3', {'textFormat': {'bold': True}})
        ws.format('E4:E6', {'textFormat': {'fontSize': 9, 'italic': True}})
        
        # ========================================
        # KPI CARDS (Rows 7-12)
        # ========================================
        
        ws.update('A7', [['KEY METRICS']])
        ws.merge_cells('A7:J7')
        ws.format('A7', {
            'textFormat': {'bold': True, 'fontSize': 14},
            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
            'horizontalAlignment': 'CENTER'
        })
        
        # KPI Card Headers
        kpi_headers = [
            ['Reviews', 'Avg Rating', 'Positive %', 'Negative %', 'Response Rate']
        ]
        ws.update('A8', kpi_headers)
        ws.format('A8:E8', {
            'textFormat': {'bold': True, 'fontSize': 11},
            'backgroundColor': {'red': 0.75, 'green': 0.75, 'blue': 0.75},
            'horizontalAlignment': 'CENTER'
        })
        
        # KPI Values (with formulas using QUERY for reliability)
        kpi_formulas = [[
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT O WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), "-")',
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT S WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), "-")',
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT X WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), "-")',
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AA WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), "-")',
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AG WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), "-")'
        ]]
        ws.update('A9', kpi_formulas)
        ws.format('A9:E9', {
            'textFormat': {'fontSize': 16, 'bold': True},
            'horizontalAlignment': 'CENTER',
            'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.0'}
        })
        
        # WoW Changes
        wow_formulas = [[
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT Q WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1) & " WoW", "")',
            '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT U WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1) & " WoW", "")',
            '', '', ''
        ]]
        ws.update('A10', wow_formulas)
        ws.format('A10:E10', {
            'textFormat': {'fontSize': 10, 'italic': True},
            'horizontalAlignment': 'CENTER'
        })
        
        # ========================================
        # FILTERED DATA TABLE (Rows 14+)
        # ========================================
        
        ws.update('A12', [['DETAILED METRICS']])
        ws.merge_cells('A12:J12')
        ws.format('A12', {
            'textFormat': {'bold': True, 'fontSize': 14},
            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
            'horizontalAlignment': 'CENTER'
        })
        
        # Filter formula (shows selected brand+week data)
        filter_formula = '=QUERY(raw_data!A:BZ, "SELECT * WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0)'
        ws.update('A14', [[filter_formula]])
        
        # ========================================
        # CHARTS SECTION (Rows 25+)
        # ========================================
        
        ws.update('A25', [['SENTIMENT BREAKDOWN']])
        ws.update('F25', [['RATING DISTRIBUTION']])
        ws.format('A25:J25', {
            'textFormat': {'bold': True, 'fontSize': 12},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        # Sentiment data for chart
        ws.update('A26', [
            ['Positive', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT V WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['Neutral', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT W WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['Negative', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT Z WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)']
        ])
        
        # Rating distribution for chart
        ws.update('F26', [
            ['5 Star', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AB WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['4 Star', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AC WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['3 Star', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AD WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['2 Star', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AE WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)'],
            ['1 Star', '=IFERROR(INDEX(QUERY(raw_data!A:BZ, "SELECT AF WHERE E = \'"&B3&"\' AND B = \'"&B4&"\'", 0), 1, 1), 0)']
        ])
        
        print("    ✅ Dashboard configured")
        return ws
    
    def setup_definitions_sheet(self, workbook):
        """Create definitions sheet with metric explanations"""
        
        print("  📖 Setting up definitions sheet...")
        
        try:
            ws = workbook.worksheet('definitions')
            print("    ✅ Sheet exists")
            return ws
        except:
            ws = workbook.add_worksheet(title='definitions', rows=50, cols=5)
            print("    ➕ Created new sheet")
        
        definitions = [
            ['METRIC DEFINITIONS', '', '', ''],
            ['', '', '', ''],
            ['Metric', 'Category', 'Definition', 'Formula'],
            ['Reviews This Week', 'Volume', 'Total reviews received in the selected week', 'COUNT(reviews)'],
            ['WoW Change', 'Volume', 'Week-over-week change in review count', '(This Week - Last Week)'],
            ['WoW Change %', 'Volume', 'Week-over-week percentage change', '(WoW Change / Last Week) * 100'],
            ['Avg Rating', 'Rating', 'Average star rating (1-5) for the week', 'AVG(rating)'],
            ['Rating WoW Change', 'Rating', 'Change in average rating vs last week', 'Avg Rating - Last Week Avg'],
            ['Positive Count', 'Sentiment', 'Reviews with 4 or 5 stars', 'COUNT(rating >= 4)'],
            ['Neutral Count', 'Sentiment', 'Reviews with exactly 3 stars', 'COUNT(rating = 3)'],
            ['Negative Count', 'Sentiment', 'Reviews with 1 or 2 stars', 'COUNT(rating <= 2)'],
            ['Response Rate', 'Response', 'Percentage of reviews with brand reply', '(Replied / Total) * 100'],
            ['Avg Response Time', 'Response', 'Average time to respond (hours)', 'AVG(reply_date - review_date)'],
            ['Verified Count', 'Source', 'Reviews from verified purchases', 'COUNT(verified = TRUE)'],
            ['Organic Count', 'Source', 'Reviews not from verified purchases', 'COUNT(verified = FALSE)'],
            ['', '', '', ''],
            ['DATA FRESHNESS', '', '', ''],
            ['Generated At', '', 'Timestamp when data was generated', ''],
            ['Snapshot Date', '', 'Start date of the ISO week', ''],
        ]
        
        ws.update('A1', definitions)
        
        # Format
        ws.format('A1:D1', {
            'textFormat': {'bold': True, 'fontSize': 14},
            'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
            'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })
        ws.format('A3:D3', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}
        })
        ws.format('A17:D17', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        ws.freeze(rows=3)
        
        print("    ✅ Definitions configured")
        return ws
    
    def append_data_row(self, ws, report_data):
        """Append one row to raw_data sheet"""
        
        rm = report_data['report_metadata']
        c = report_data['company']
        rv = report_data['week_stats']['review_volume']
        rp = report_data['week_stats']['rating_performance']
        s = report_data['week_stats']['sentiment']
        rd = report_data['week_stats']['rating_distribution']
        resp = report_data['week_stats']['response_performance']
        ca = report_data['week_stats']['content_analysis']
        
        # Helper functions
        def safe_float(val):
            if val is None:
                return ''
            if isinstance(val, Decimal):
                return float(val)
            return val
        
        def get_theme(themes, index):
            """Get theme at index or return empty"""
            if themes and len(themes) > index:
                return themes[index].get('topic', ''), themes[index].get('count', 0)
            return '', 0
        
        def get_lang(lang_dict, index):
            """Get language at index from dict"""
            sorted_langs = sorted(lang_dict.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_langs) > index:
                return sorted_langs[index][0], sorted_langs[index][1]
            return '', 0
        
        def get_country(countries, index):
            """Get country at index"""
            if countries and len(countries) > index:
                return countries[index]['country'], countries[index]['review_count']
            return '', 0
        
        # Extract top languages
        lang_dict = rv.get('by_language', {})
        lang1, lang1_count = get_lang(lang_dict, 0)
        lang2, lang2_count = get_lang(lang_dict, 1)
        lang3, lang3_count = get_lang(lang_dict, 2)
        
        # Extract top countries
        countries = rv.get('by_country', [])
        country1, country1_count = get_country(countries, 0)
        country2, country2_count = get_country(countries, 1)
        country3, country3_count = get_country(countries, 2)
        
        # Extract themes
        pos_themes = ca.get('positive_themes', [])
        neg_themes = ca.get('negative_themes', [])
        
        pos1, pos1_count = get_theme(pos_themes, 0)
        pos2, pos2_count = get_theme(pos_themes, 1)
        pos3, pos3_count = get_theme(pos_themes, 2)
        neg1, neg1_count = get_theme(neg_themes, 0)
        neg2, neg2_count = get_theme(neg_themes, 1)
        neg3, neg3_count = get_theme(neg_themes, 2)
        
        # Build row
        row = [
            # Identifiers
            rm['week_start'],  # snapshot_date
            rm['iso_week'],
            rm['week_start'],
            rm['week_end'],
            c['brand_name'],  # brand_id (using name for now)
            c['brand_name'],
            c.get('website', ''),
            c.get('business_id', ''),
            
            # Company Info
            safe_float(c.get('trust_score')),
            c.get('total_reviews_alltime', 0),
            c.get('is_claimed', False),
            ', '.join(c.get('categories', [])[:3]),
            c.get('logo_url', ''),
            c.get('star_rating_svg', ''),
            
            # Review Volume
            rv['total_this_week'],
            rv.get('total_last_week', 0),
            rv.get('wow_change', 0),
            safe_float(rv.get('wow_change_pct')),
            
            # Rating Performance
            safe_float(rp['avg_rating_this_week']),
            safe_float(rp.get('avg_rating_last_week')),
            safe_float(rp.get('wow_change')),
            
            # Sentiment
            s['positive']['count'],
            safe_float(s['positive']['percentage']),
            s['neutral']['count'],
            safe_float(s['neutral']['percentage']),
            s['negative']['count'],
            safe_float(s['negative']['percentage']),
            
            # Rating Distribution
            rd['5_stars'],
            rd['4_stars'],
            rd['3_stars'],
            rd['2_stars'],
            rd['1_star'],
            
            # Response Performance
            resp.get('reviews_with_response', 0),
            safe_float(resp.get('response_rate_pct', 0)),
            safe_float(resp.get('avg_response_time_hours')),
            safe_float(resp.get('avg_response_time_days')),
            
            # Sources
            rv.get('by_source', {}).get('verified_invited', 0),
            rv.get('by_source', {}).get('organic', 0),
            
            # Languages
            lang1, lang1_count,
            lang2, lang2_count,
            lang3, lang3_count,
            
            # Countries
            country1, country1_count,
            country2, country2_count,
            country3, country3_count,
            
            # Themes
            pos1, pos1_count,
            pos2, pos2_count,
            pos3, pos3_count,
            neg1, neg1_count,
            neg2, neg2_count,
            neg3, neg3_count,
            
            # AI Summary
            c.get('ai_summary', {}).get('summary_text', '')[:500] if c.get('ai_summary') else '',
            
            # Metadata
            rm['generated_at']
        ]
        
        ws.append_row(row)
        print(f"    ✅ Appended: {c['brand_name']} | {rm['iso_week']}")
    
    def upload_report(self, report_data):
        """
        Main upload function - append one report to the spreadsheet
        
        Args:
            report_data: Dict from generate_weekly_report()
        
        Returns:
            spreadsheet_id: ID of the uploaded spreadsheet
        """
        
        print("\n" + "="*70)
        print("UPLOADING TO GOOGLE SHEETS")
        print("="*70 + "\n")
        
        brand_name = report_data['company']['brand_name']
        iso_week = report_data['report_metadata']['iso_week']
        
        print(f"📊 {brand_name} | {iso_week}")
        
        # Get or create spreadsheet
        spreadsheet_id = self.find_or_create_spreadsheet()
        workbook = self.gc.open_by_key(spreadsheet_id)
        
        # Setup structure (idempotent)
        raw_data_ws = self.setup_raw_data_sheet(workbook)
        self.setup_dashboard_sheet(workbook, spreadsheet_id)
        self.setup_definitions_sheet(workbook)
        
        # Append data row
        self.append_data_row(raw_data_ws, report_data)
        
        print("\n" + "="*70)
        print("✅ UPLOAD COMPLETE")
        print("="*70)
        print(f"\n🔗 View Dashboard:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0")
        print(f"\n💡 Next Steps:")
        print(f"   1. Go to dashboard sheet")
        print(f"   2. Click cell B3 → Data > Data validation")
        print(f"      Range: raw_data!E2:E (brand names)")
        print(f"   3. Click cell B4 → Data > Data validation")
        print(f"      Range: raw_data!B2:B (ISO weeks)")
        print(f"   4. Select brand & week to see metrics!\n")
        
        return spreadsheet_id


# CLI usage
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python sheets_uploader_v2.py <report.json>")
        sys.exit(1)
    
    report_file = sys.argv[1]
    
    with open(report_file, 'r') as f:
        report_data = json.load(f)
    
    uploader = SheetsUploader()
    uploader.upload_report(report_data)