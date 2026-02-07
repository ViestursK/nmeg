#!/usr/bin/env python3
"""
Sheets Uploader V3 - HTML Report Structure in Google Sheets
- raw_data: Full weekly data (including AI summary + topics)
- dashboard: Visual report display (like old HTML) with brand/week selectors
"""

import os
import json
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()


class SheetsUploaderV3:
    """Upload weekly reports to Google Sheets with visual dashboard"""
    
    def __init__(self):
        """Initialize with credentials and find/create spreadsheet"""
        
        # Configuration
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Dashboard")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS")
        
        # Handle relative paths
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir) if os.path.basename(current_dir) == 'sheets' else current_dir
            creds_path = os.path.join(project_root, creds_path)
        
        # Setup credentials
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.gc = gspread.authorize(self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
    
    def find_or_create_spreadsheet(self):
        """Find existing spreadsheet or create new one"""
        
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
        
        print(f"➕ Creating new spreadsheet: {self.spreadsheet_name}")
        spreadsheet = self.gc.create(self.spreadsheet_name, folder_id=self.folder_id)
        return spreadsheet.id
    
    def setup_raw_data_sheet(self, workbook):
        """Setup raw_data sheet with full data structure"""
        
        print("  📊 Setting up raw_data sheet...")
        
        try:
            ws = workbook.worksheet('raw_data')
            print("    ✅ Sheet exists")
        except:
            ws = workbook.add_worksheet(title='raw_data', rows=10000, cols=90)
            print("    ➕ Created new sheet")
        
        # Check if headers exist
        try:
            existing_headers = ws.row_values(1)
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
                
                # Languages (top 3)
                'top_language_1', 'top_language_1_count',
                'top_language_2', 'top_language_2_count',
                'top_language_3', 'top_language_3_count',
                
                # Countries (top 3)
                'top_country_1', 'top_country_1_count',
                'top_country_2', 'top_country_2_count',
                'top_country_3', 'top_country_3_count',
                
                # Themes (top 3 positive/negative)
                'positive_theme_1', 'positive_theme_1_count',
                'positive_theme_2', 'positive_theme_2_count',
                'positive_theme_3', 'positive_theme_3_count',
                'negative_theme_1', 'negative_theme_1_count',
                'negative_theme_2', 'negative_theme_2_count',
                'negative_theme_3', 'negative_theme_3_count',
                
                # AI Summary & Topics (NEW - full data)
                'ai_summary_full',
                'ai_summary_updated_at',
                'ai_summary_language',
                'ai_summary_model_version',
                'top_mentions',  # JSON array as text
                
                # Metadata
                'generated_at'
            ]
            
            ws.update('A1', [headers])
            
            # Format header row
            ws.format('A1:CZ1', {
                'textFormat': {'bold': True, 'fontSize': 10},
                'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })
            
            ws.freeze(rows=1)
        
        return ws
    
    
    
    def append_data_row(self, ws, report_data):
        """Append one weekly report to raw_data sheet"""
        
        print("  💾 Appending data row...")
        
        c = report_data['company']
        rm = report_data['report_metadata']
        
        # Check if data is nested under week_stats or at root level
        if 'week_stats' in report_data:
            ws = report_data['week_stats']
            rv = ws['review_volume']
            rp = ws['rating_performance']
            s = ws['sentiment']
            rd = ws['rating_distribution']
            resp = ws['response_performance']
            ca = ws['content_analysis']
        else:
            # Legacy structure
            rv = report_data['review_volume']
            rp = report_data['rating_performance']
            s = report_data['sentiment']
            rd = report_data['rating_distribution']
            resp = report_data['response_performance']
            ca = report_data['content_analysis']
        
        # Helper functions
        def safe_float(val):
            try:
                return float(val) if val is not None else 0
            except:
                return 0
        
        def get_top_item(arr, idx):
            if arr and len(arr) > idx:
                item = arr[idx]
                return item.get('language' if 'language' in item else 'country', ''), item.get('count', 0)
            return '', 0
        
        def get_theme(arr, idx):
            if arr and len(arr) > idx:
                return arr[idx].get('topic', ''), arr[idx].get('count', 0)
            return '', 0
        
        # Extract top items
        langs = rv.get('by_language', [])
        countries = rv.get('by_country', [])
        
        lang1, lang1_count = get_top_item(langs, 0)
        lang2, lang2_count = get_top_item(langs, 1)
        lang3, lang3_count = get_top_item(langs, 2)
        
        country1, country1_count = get_top_item(countries, 0)
        country2, country2_count = get_top_item(countries, 1)
        country3, country3_count = get_top_item(countries, 2)
        
        # Extract themes
        pos_themes = ca.get('positive_themes', [])
        neg_themes = ca.get('negative_themes', [])
        
        pos1, pos1_count = get_theme(pos_themes, 0)
        pos2, pos2_count = get_theme(pos_themes, 1)
        pos3, pos3_count = get_theme(pos_themes, 2)
        neg1, neg1_count = get_theme(neg_themes, 0)
        neg2, neg2_count = get_theme(neg_themes, 1)
        neg3, neg3_count = get_theme(neg_themes, 2)
        
        # Extract AI summary and topics (NEW)
        ai_summary_data = c.get('ai_summary', {}) or {}
        ai_summary_text = ai_summary_data.get('summary_text', '')
        ai_summary_updated = ai_summary_data.get('updated_at', '')
        ai_summary_lang = ai_summary_data.get('language', '')
        ai_summary_model = ai_summary_data.get('model_version', '')
        
        # Format topics as comma-separated list (from top_mentions_overall)
        topics_list = c.get('top_mentions_overall', []) or c.get('topics', [])
        topics_text = ', '.join(topics_list) if topics_list else ''
        
        # Build row
        row = [
            # Identifiers
            rm['week_start'],
            rm['iso_week'],
            rm['week_start'],
            rm['week_end'],
            c['brand_name'],
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
            
            # AI Summary & Topics (NEW - full data)
            ai_summary_text,
            ai_summary_updated,
            ai_summary_lang,
            ai_summary_model,
            topics_text,
            
            # Metadata
            rm['generated_at']
        ]
        
        ws.append_row(row)
        print(f"    ✅ Appended: {c['brand_name']} | {rm['iso_week']}")
    
    def upload_report(self, report_data):
        """
        Main upload function
        
        Args:
            report_data: Dict from generate_weekly_report()
        
        Returns:
            spreadsheet_id
        """
        
        print("\n" + "="*70)
        print("UPLOADING TO GOOGLE SHEETS V3")
        print("="*70 + "\n")
        
        brand_name = report_data['company']['brand_name']
        iso_week = report_data['report_metadata']['iso_week']
        
        print(f"📊 {brand_name} | {iso_week}")
        
        # Get or create spreadsheet
        spreadsheet_id = self.find_or_create_spreadsheet()
        workbook = self.gc.open_by_key(spreadsheet_id)
        
        # Setup structure
        raw_data_ws = self.setup_raw_data_sheet(workbook)
        self.setup_dashboard_sheet(workbook, spreadsheet_id)
        
        # Append data
        self.append_data_row(raw_data_ws, report_data)
        
        print("\n" + "="*70)
        print("✅ UPLOAD COMPLETE")
        print("="*70)
        print(f"\n🔗 View Dashboard:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0")
        print(f"\n💡 Setup Instructions:")
        print(f"   1. Open dashboard sheet")
        print(f"   2. Click B3 → Data > Data validation")
        print(f"      Range: raw_data!F2:F (brand names)")
        print(f"   3. Click B4 → Data > Data validation")
        print(f"      Range: raw_data!B2:B (ISO weeks)")
        print(f"   4. Select brand + week to view report!\n")
        
        return spreadsheet_id


if __name__ == "__main__":
    print("Import this module and use SheetsUploaderV3 class")