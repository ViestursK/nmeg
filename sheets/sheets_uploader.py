#!/usr/bin/env python3
"""
Unified Trustpilot Reporting to Google Sheets
- One master spreadsheet for all brands
- Each brand gets its own snapshot tab
- Charts are generated per week per brand
- Charts can be linked in Google Docs reports
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
import json

load_dotenv()

class UnifiedSheetsUploader:
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Master Report")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS in .env")
        
        # Handle relative paths
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
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
        """Find master spreadsheet (must be created manually by user)"""
        
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
            raise FileNotFoundError(
                f"❌ Master sheet '{self.spreadsheet_name}' not found in folder.\n"
                f"   Please create it manually at:\n"
                f"   https://drive.google.com/drive/folders/{self.folder_id}\n"
                f"   Name it exactly: '{self.spreadsheet_name}'"
            )
        
        print(f"📄 Found master sheet: {files[0]['name']}")
        return files[0]['id']
    
    def get_or_create_brand_tab(self, workbook, brand_name):
        """Get or create tab for a specific brand"""
        
        try:
            ws = workbook.worksheet(brand_name)
            print(f"  ✓ Found tab: {brand_name}")
            return ws
        except:
            print(f"  ➕ Creating tab: {brand_name}")
            ws = workbook.add_worksheet(title=brand_name, rows=5000, cols=50)
            
            # Setup headers with ALL data fields (no charts)
            headers = [
                # Week & Brand Info
                'iso_week', 'week_start', 'week_end', 
                'brand_name', 'business_id', 'website', 'logo_url', 'trust_score', 'stars',
                'total_reviews_all_time', 'is_claimed',
                
                # Volume Metrics
                'total_reviews', 'total_reviews_last_week', 'wow_change', 'wow_change_pct',
                
                # Rating Metrics
                'avg_rating', 'avg_rating_last_week', 'wow_rating_change',
                
                # Sentiment
                'positive_count', 'positive_pct', 'neutral_count', 'neutral_pct',
                'negative_count', 'negative_pct',
                
                # Rating Distribution
                'rating_5', 'rating_4', 'rating_3', 'rating_2', 'rating_1',
                
                # Response Performance
                'reviews_with_reply', 'reviews_without_reply', 'response_rate_pct', 
                'avg_response_hours', 'avg_response_days',
                
                # Source Split
                'verified_count', 'organic_count', 'reviews_edited',
                
                # Language Breakdown (JSON string)
                'languages_json',
                
                # Top Countries (formatted string)
                'top_countries',
                
                # Themes
                'top_negative_themes', 'top_positive_themes', 'top_neutral_themes',
                
                # Metadata
                'categories', 'ai_summary',
                
                # Timestamp
                'generated_at'
            ]
            
            ws.update(values=[headers], range_name='A1')
            
            # Format header
            ws.format('A1:AN1', {
                'textFormat': {'bold': True, 'fontSize': 11},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            
            # Freeze header
            ws.freeze(rows=1)
            
            return ws
    
    def format_themes_list(self, themes):
        """Format themes array into readable string"""
        if not themes:
            return ""
        return ", ".join([f"{t['topic']} ({t['count']})" for t in themes[:5]])
    
    def upload_report(self, brand_name, report_data):
        """Upload report to unified master sheet"""
        
        print(f"\n{'='*70}")
        print(f"UPLOADING TO MASTER SHEET")
        print(f"{'='*70}\n")
        print(f"Brand: {brand_name}")
        print(f"Week: {report_data['report_metadata']['iso_week']}\n")
        
        # Get master sheet (must exist)
        spreadsheet_id = self.find_master_sheet()
        print(f"🔗 https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")
        
        # Open workbook
        workbook = self.gc.open_by_key(spreadsheet_id)
        
        # Get or create brand tab
        ws = self.get_or_create_brand_tab(workbook, brand_name)
        
        # Extract data
        rm = report_data['report_metadata']
        c = report_data['company']
        rv = report_data['week_stats']['review_volume']
        rp = report_data['week_stats']['rating_performance']
        s = report_data['week_stats']['sentiment']
        rd = report_data['week_stats']['rating_distribution']
        resp = report_data['week_stats']['response_performance']
        ca = report_data['week_stats']['content_analysis']
        
        # Build row data with ALL fields (convert Decimals to float/int)
        def safe_numeric(val):
            """Convert Decimal to float, handle None"""
            if val is None or val == '':
                return ''
            if isinstance(val, Decimal):
                return float(val)
            return val
        
        row_data = [
            # Week & Brand Info
            rm['iso_week'],
            rm['week_start'],
            rm['week_end'],
            c['brand_name'],
            c.get('business_id', ''),
            c.get('website', ''),
            c.get('logo_url', ''),
            safe_numeric(c.get('trust_score', '')),
            safe_numeric(c.get('stars', '')),
            safe_numeric(c.get('total_reviews_all_time', '')),
            c.get('is_claimed', ''),
            
            # Volume Metrics
            rv['total_this_week'],
            rv['total_last_week'],
            rv['wow_change'],
            safe_numeric(rv.get('wow_change_pct', '')),
            
            # Rating Metrics
            safe_numeric(rp['avg_rating_this_week']),
            safe_numeric(rp.get('avg_rating_last_week', '')),
            safe_numeric(rp.get('wow_change', '')),
            
            # Sentiment
            s['positive']['count'],
            safe_numeric(s['positive']['percentage']),
            s['neutral']['count'],
            safe_numeric(s['neutral']['percentage']),
            s['negative']['count'],
            safe_numeric(s['negative']['percentage']),
            
            # Rating Distribution
            rd['5_stars'],
            rd['4_stars'],
            rd['3_stars'],
            rd['2_stars'],
            rd['1_star'],
            
            # Response Performance
            resp['reviews_with_response'],
            resp.get('reviews_without_response', ''),
            safe_numeric(resp['response_rate_pct']),
            safe_numeric(resp.get('avg_response_time_hours', '')),
            safe_numeric(resp.get('avg_response_time_days', '')),
            
            # Source Split
            rv['by_source']['verified_invited'],
            rv['by_source']['organic'],
            resp['reviews_edited'],
            
            # Language Breakdown (as JSON string, convert Decimals to float)
            json.dumps({k: int(v) if isinstance(v, int) else float(v) if isinstance(v, (Decimal, float)) else v 
                       for k, v in rv.get('by_language', {}).items()}),
            
            # Top Countries (formatted from list of dicts)
            ', '.join([f"{country['country']} ({country['review_count']})" for country in rv.get('by_country', [])[:10]]),
            
            # Themes
            self.format_themes_list(ca['negative_themes']),
            self.format_themes_list(ca['positive_themes']),
            self.format_themes_list(ca.get('neutral_themes', [])),
            
            # Metadata - categories might be list of dicts like [{"name": "..."}] or strings
            ', '.join([cat if isinstance(cat, str) else cat.get('name', str(cat)) for cat in c.get('categories', [])]),
            c.get('ai_summary', {}).get('summary_text', '')[:1000] if c.get('ai_summary') else '',
            
            # Timestamp
            rm['generated_at']
        ]
        
        # Check if week exists and insert/update row
        all_data = ws.get_all_values()
        iso_week = rm['iso_week']
        row_index = None
        
        for idx, row in enumerate(all_data[1:], start=2):
            if row and row[0] == iso_week:
                row_index = idx
                break
        
        if row_index:
            # Update existing row
            ws.update(values=[row_data], range_name=f'A{row_index}')
            print(f"  ↻ Updated week {iso_week}")
        else:
            # Append new row
            ws.append_row(row_data)
            print(f"  ✓ Added week {iso_week}")
        
        print(f"\n{'='*70}")
        print(f"✅ UPLOAD COMPLETE")
        print(f"{'='*70}")
        print(f"🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"📊 Tab: {brand_name}\n")
        
        return spreadsheet_id


def main():
    """CLI entry point"""
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python unified_sheets_uploader.py <brand_name> <report_json_file>")
        print("  python unified_sheets_uploader.py <brand_name> <company_domain> <iso_week>")
        print("")
        print("Examples:")
        print("  python unified_sheets_uploader.py 'KetoGo' weekly_report_ketogo_app_2026-W04.json")
        print("  python unified_sheets_uploader.py 'KetoGo' ketogo.app 2026-W04")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    
    # Check if second arg is JSON file or company domain
    if sys.argv[2].endswith('.json'):
        # Load from JSON file
        report_file = sys.argv[2]
        
        if not os.path.exists(report_file):
            print(f"❌ Report file not found: {report_file}")
            sys.exit(1)
        
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
    
    else:
        # Generate from database
        if len(sys.argv) < 4:
            print("❌ Missing iso_week parameter")
            sys.exit(1)
        
        company_domain = sys.argv[2]
        iso_week = sys.argv[3]
        
        # Import from parent directory
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, parent_dir)
        from generate_weekly_report import generate_weekly_report
        
        print(f"📊 Generating report from database...")
        report_data = generate_weekly_report(company_domain, iso_week)
        
        if not report_data:
            print(f"❌ Failed to generate report")
            sys.exit(1)
    
    # Upload
    uploader = UnifiedSheetsUploader()
    uploader.upload_report(brand_name, report_data)


if __name__ == "__main__":
    main()