#!/usr/bin/env python3
"""
Sheets Uploader - Smart Update Logic
Handles daily updates for current week without duplicates
"""

import os
import json
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()


class DashboardSheetsUploader:
    """Upload weekly reports to Google Sheets with smart deduplication"""
    
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Report")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS")
        
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) == 'sheets' else current_dir
            creds_path = os.path.join(project_root, creds_path)
        
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.gc = gspread.authorize(self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        # Cache existing data
        self._existing_data_cache = None
    
    def find_or_create_spreadsheet(self):
        """Find existing spreadsheet (does not create new ones)"""
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
            print(f"✅ Found: {files[0]['name']}")
            return files[0]['id']
        
        raise FileNotFoundError(
            f"❌ Spreadsheet '{self.spreadsheet_name}' not found in folder.\n"
            f"   Create it manually first:\n"
            f"   1. Open https://drive.google.com/drive/folders/{self.folder_id}\n"
            f"   2. Create new Google Sheet\n"
            f"   3. Name it: {self.spreadsheet_name}\n"
            f"   4. Run script again"
        )
    
    def setup_raw_data_sheet(self, workbook):
        """Setup raw_data with simplified structure"""
        print("  📊 Setting up raw_data...")
        
        try:
            ws = workbook.worksheet('raw_data')
            print("    ✅ Sheet exists")
        except gspread.exceptions.WorksheetNotFound:
            ws = workbook.add_worksheet(title='raw_data', rows=10000, cols=45)
            print("    ➕ Created sheet")
        except Exception as e:
            print(f"    ⚠️  Error accessing sheet: {e}")
            # Try to get any sheet with 'raw' in the name
            for sheet in workbook.worksheets():
                if 'raw' in sheet.title.lower():
                    ws = sheet
                    print(f"    ✅ Using sheet: {sheet.title}")
                    break
            else:
                raise
        
        # Check headers
        try:
            existing = ws.row_values(1)
            has_headers = len(existing) >= 10
        except:
            has_headers = False
        
        if not has_headers:
            print("    📝 Writing headers...")
            headers = [
                # Identifiers
                'iso_week', 'week_start', 'week_end', 'brand_name',
                'business_id', 'website_url',
                
                # Company info
                'trust_score', 'total_reviews_alltime', 'stars', 'is_claimed',
                'categories', 'logo_url', 'star_rating_svg',
                
                # Week stats
                'total_reviews', 'avg_rating',
                'positive_count', 'positive_pct',
                'neutral_count', 'neutral_pct',
                'negative_count', 'negative_pct',
                
                # Rating distribution
                'rating_5', 'rating_4', 'rating_3', 'rating_2', 'rating_1',
                
                # Response
                'reviews_with_reply', 'response_rate_pct', 'avg_response_hours',
                
                # Sources
                'verified_count', 'organic_count',
                
                # Top languages (3)
                'lang_1', 'lang_1_count',
                'lang_2', 'lang_2_count',
                'lang_3', 'lang_3_count',
                
                # Top countries (3)
                'country_1', 'country_1_count',
                'country_2', 'country_2_count',
                'country_3', 'country_3_count',
                
                # Themes (all as comma-separated)
                'positive_themes',
                'negative_themes',
                
                # AI
                'ai_summary', 'ai_topics',
                
                # Meta
                'generated_at'
            ]
            
            ws.update(range_name='A1', values=[headers])
            ws.format('A1:BZ1', {
                'textFormat': {'bold': True, 'fontSize': 10},
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            ws.freeze(rows=1)
        
        return ws
    
    def get_existing_data(self, ws):
        """Get existing brand+week combinations with row numbers"""
        if self._existing_data_cache is not None:
            print(f"  ✓ Using cached data ({len(self._existing_data_cache)} records)")
            return self._existing_data_cache
        
        print("  🔍 Reading data from sheets...")
        
        try:
            all_values = ws.get_all_values()
        except:
            self._existing_data_cache = {}
            return self._existing_data_cache
        
        if len(all_values) <= 1:
            # No data or only headers
            self._existing_data_cache = {}
            return self._existing_data_cache
        
        # Build index: {brand_name|iso_week: {row_num, total_reviews}}
        existing = {}
        
        for row_num, row in enumerate(all_values[1:], start=2):  # Skip header, start at row 2
            if len(row) < 14:  # Not enough columns
                continue
            
            iso_week = row[0]      # Column A
            brand_name = row[3]    # Column D
            total_reviews = row[13] # Column N (total_reviews)
            
            if iso_week and brand_name:
                key = f"{brand_name}|{iso_week}"
                existing[key] = {
                    'row_num': row_num,
                    'total_reviews': int(total_reviews) if total_reviews and total_reviews.isdigit() else 0
                }
        
        print(f"    Found {len(existing)} existing week records")
        self._existing_data_cache = existing
        return existing
    
    def build_data_row(self, report_data):
        """Build row data from report (extracted for reuse)"""
        def safe_float(val):
            try:
                return float(val) if val is not None else 0
            except:
                return 0
        
        def get_top(arr, idx, key):
            if arr and len(arr) > idx:
                return arr[idx].get(key, ''), arr[idx].get('count', 0)
            return '', 0
        
        # Parse JSON fields
        langs = json.loads(report_data.get('language_breakdown_json', '{}'))
        langs_sorted = sorted(langs.items(), key=lambda x: x[1], reverse=True)
        
        countries = json.loads(report_data.get('country_breakdown_json', '[]'))
        
        pos_themes = json.loads(report_data.get('positive_themes_json', '[]'))
        neg_themes = json.loads(report_data.get('negative_themes_json', '[]'))
        
        # Top items
        lang1 = langs_sorted[0][0] if len(langs_sorted) > 0 else ''
        lang1_count = langs_sorted[0][1] if len(langs_sorted) > 0 else 0
        lang2 = langs_sorted[1][0] if len(langs_sorted) > 1 else ''
        lang2_count = langs_sorted[1][1] if len(langs_sorted) > 1 else 0
        lang3 = langs_sorted[2][0] if len(langs_sorted) > 2 else ''
        lang3_count = langs_sorted[2][1] if len(langs_sorted) > 2 else 0
        
        country1, country1_count = get_top(countries, 0, 'country')
        country2, country2_count = get_top(countries, 1, 'country')
        country3, country3_count = get_top(countries, 2, 'country')
        
        # Format all themes as comma-separated strings
        def format_themes(themes):
            return ', '.join([f"{t.get('topic', '')} ({t.get('count', 0)})" for t in themes])
        
        positive_themes_str = format_themes(pos_themes)
        negative_themes_str = format_themes(neg_themes)
        
        total = report_data['total_reviews']
        
        return [
            # Identifiers
            report_data['iso_week'],
            report_data['week_start'],
            report_data['week_end'],
            report_data['brand_name'],
            report_data.get('business_id', ''),
            report_data.get('website_url', ''),
            
            # Company
            safe_float(report_data.get('trust_score')),
            report_data.get('total_reviews_all_time_tp', 0),
            report_data.get('stars', 0),
            report_data.get('is_claimed', False),
            ', '.join([str(c) for c in report_data.get('categories', [])[:3]]),
            report_data.get('logo_url', ''),
            report_data.get('star_rating_svg', ''),
            
            # Week stats
            total,
            safe_float(report_data['avg_rating']),
            report_data['positive_reviews'],
            round((report_data['positive_reviews'] / total * 100), 2) if total else 0,
            report_data['neutral_reviews'],
            round((report_data['neutral_reviews'] / total * 100), 2) if total else 0,
            report_data['negative_reviews'],
            round((report_data['negative_reviews'] / total * 100), 2) if total else 0,
            
            # Rating dist
            report_data['rating_5'],
            report_data['rating_4'],
            report_data['rating_3'],
            report_data['rating_2'],
            report_data['rating_1'],
            
            # Response
            report_data['reviews_with_response'],
            safe_float(report_data['response_rate_pct']),
            safe_float(report_data.get('avg_response_time_hours')),
            
            # Sources
            report_data['verified_reviews'],
            report_data['organic_reviews'],
            
            # Languages
            lang1, lang1_count,
            lang2, lang2_count,
            lang3, lang3_count,
            
            # Countries
            country1, country1_count,
            country2, country2_count,
            country3, country3_count,
            
            # Themes (all as comma-separated)
            positive_themes_str,
            negative_themes_str,
            
            # AI
            report_data.get('ai_summary', ''),
            ', '.join([t if isinstance(t, str) else str(t) for t in report_data.get('ai_topics', [])]),
            
            # Meta
            report_data['generated_at']
        ]
    
    def upload_report(self, brand_name, report_data, workbook=None, raw_data_ws=None, existing=None):
        """Main upload function with smart update logic"""
        print(f"\n{'='*70}")
        print(f"UPLOADING: {brand_name} | {report_data['iso_week']}")
        print(f"{'='*70}\n")
        
        # Only fetch these once per batch
        if workbook is None:
            spreadsheet_id = self.find_or_create_spreadsheet()
            workbook = self.gc.open_by_key(spreadsheet_id)
        
        if raw_data_ws is None:
            raw_data_ws = self.setup_raw_data_sheet(workbook)
        
        # Get existing data ONLY if not provided
        if existing is None:
            print("  ⚠️  No existing data provided - reading from sheets")
            existing = self.get_existing_data(raw_data_ws)
        else:
            print(f"  ✓ Using provided data ({len(existing)} records)")
        # Don't invalidate cache - just update it later
        
        # Check if this brand+week exists
        key = f"{brand_name}|{report_data['iso_week']}"
        
        # Build row data
        row_data = self.build_data_row(report_data)
        new_total_reviews = report_data['total_reviews']
        
        if key in existing:
            # Already exists - check if changed
            old_total_reviews = existing[key]['total_reviews']
            row_num = existing[key]['row_num']
            
            if new_total_reviews == old_total_reviews:
                print(f"  ⏭️  SKIP: {brand_name} | {report_data['iso_week']} - no changes ({new_total_reviews} reviews)")
            else:
                # Data changed - UPDATE existing row
                print(f"  🔄 UPDATE: Row {row_num} - {old_total_reviews} → {new_total_reviews} reviews")
                raw_data_ws.update(range_name=f'A{row_num}', values=[row_data])
                print(f"    ✅ Updated")
                
                # Update cache in-place
                existing[key] = {'row_num': row_num, 'total_reviews': new_total_reviews}
        else:
            # New entry - INSERT
            print(f"  ➕ INSERT: {brand_name} | {report_data['iso_week']} ({new_total_reviews} reviews)")
            raw_data_ws.append_row(row_data)
            print(f"    ✅ Appended")
            
            # Update cache in-place (new row number = existing count + 2 for header)
            new_row_num = len(existing) + 2
            existing[key] = {'row_num': new_row_num, 'total_reviews': new_total_reviews}
        
        print(f"\n✅ UPLOAD COMPLETE")
        
        # Return reusable objects for batch operations
        return {
            'spreadsheet_id': workbook.id if hasattr(workbook, 'id') else spreadsheet_id,
            'workbook': workbook,
            'raw_data_ws': raw_data_ws,
            'existing': existing
        }


if __name__ == "__main__":
    print("Import and use DashboardSheetsUploader class")