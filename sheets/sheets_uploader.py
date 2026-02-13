#!/usr/bin/env python3
"""
Sheets Uploader - Simplified Structure
Single week data only, historic KPIs calculated in sheets
"""

import os
import json
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()


class DashboardSheetsUploader:
    """Upload weekly reports to Google Sheets with simple structure"""
    
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
        except:
            ws = workbook.add_worksheet(title='raw_data', rows=10000, cols=45)
            print("    ➕ Created sheet")
        
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
            
            ws.update('A1', [headers])
            ws.format('A1:BZ1', {
                'textFormat': {'bold': True, 'fontSize': 10},
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            ws.freeze(rows=1)
        
        return ws
    
    def append_data_row(self, ws, report_data):
        """Append weekly report to raw_data"""
        print("  💾 Appending data...")
        
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
        
        row = [
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
        
        ws.append_row(row)
        print(f"    ✅ {report_data['brand_name']} | {report_data['iso_week']}")
    
    def upload_report(self, brand_name, report_data):
        """Main upload function"""
        print(f"\n{'='*70}")
        print(f"UPLOADING: {brand_name} | {report_data['iso_week']}")
        print(f"{'='*70}\n")
        
        spreadsheet_id = self.find_or_create_spreadsheet()
        workbook = self.gc.open_by_key(spreadsheet_id)
        
        raw_data_ws = self.setup_raw_data_sheet(workbook)
        self.append_data_row(raw_data_ws, report_data)
        
        print(f"\n✅ UPLOAD COMPLETE")
        print(f"🔗 https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")
        
        return spreadsheet_id


if __name__ == "__main__":
    print("Import and use DashboardSheetsUploader class")