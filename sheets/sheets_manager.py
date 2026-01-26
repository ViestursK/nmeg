"""
Google Sheets Manager for Trustpilot Brand Reports
Handles sheet creation, updates, and chart generation
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("⚠️  Google API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client --break-system-packages")
    raise

from config import (
    TAB_BRAND_OVERVIEW, TAB_ALL_TIME_STATS, TAB_WEEKLY_SNAPSHOTS, TAB_CHART_DATA,
    WEEKLY_SNAPSHOT_COLUMNS, WEEKLY_COLUMN_PATHS,
    CHART_RATING_TREND, CHART_VOLUME_TREND, CHART_SENTIMENT, 
    CHART_RATING_DIST, CHART_NEGATIVE_THEMES
)

load_dotenv()

class GoogleSheetsManager:
    """Manages Google Sheets for brand reporting"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self._setup_credentials()
        
    def _setup_credentials(self):
        """Setup Google Sheets API credentials"""
        creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        
        if not creds_path:
            raise ValueError("GOOGLE_SHEETS_CREDENTIALS not set in .env")
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        print("✅ Google Sheets API authenticated")
    
    def create_brand_sheet(self, brand_name: str) -> str:
        """
        Create a new Google Sheet for a brand with all required tabs
        
        Args:
            brand_name: Brand name for sheet title
            
        Returns:
            spreadsheet_id: ID of created sheet
        """
        print(f"\n📊 Creating Google Sheet for {brand_name}...")
        
        # Get folder ID from environment
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not folder_id:
            raise ValueError(
                "GOOGLE_DRIVE_FOLDER_ID not set in .env\n"
                "Please create a Google Drive folder, share it with your service account, "
                "and add the folder ID to .env"
            )
        
        # Create spreadsheet via Drive API (inside shared folder)
        file_metadata = {
            'name': f'Trustpilot Report - {brand_name}',
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id]
        }
        
        file = self.drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        spreadsheet_id = file['id']
        
        print(f"  ✓ Created spreadsheet: {spreadsheet_id}")
        
        # Now add the tabs via Sheets API
        # First, delete the default "Sheet1"
        # Then add our custom tabs
        sheets_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        default_sheet_id = sheets_metadata['sheets'][0]['properties']['sheetId']
        
        requests = [
            # Add our tabs
            {'addSheet': {'properties': {'title': TAB_BRAND_OVERVIEW}}},
            {'addSheet': {'properties': {'title': TAB_ALL_TIME_STATS}}},
            {'addSheet': {'properties': {'title': TAB_WEEKLY_SNAPSHOTS}}},
            {'addSheet': {'properties': {'title': TAB_CHART_DATA}}},
            # Delete default Sheet1
            {'deleteSheet': {'sheetId': default_sheet_id}}
        ]
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        
        print(f"  ✓ Created tabs")
        
        # Setup tabs
        self._setup_weekly_snapshots_tab(spreadsheet_id)
        self._setup_chart_data_tab(spreadsheet_id)
        
        print(f"✅ Sheet ready: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        return spreadsheet_id
    
    def _setup_weekly_snapshots_tab(self, spreadsheet_id: str):
        """Setup Weekly_Snapshots tab with headers and formatting"""
        
        # Write headers
        headers = [WEEKLY_SNAPSHOT_COLUMNS]
        
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'{TAB_WEEKLY_SNAPSHOTS}!A1',
            valueInputOption='RAW',
            body={'values': headers}
        ).execute()
        
        # Format header row
        requests = [
            {
                'repeatCell': {
                    'range': {
                        'sheetId': self._get_sheet_id(spreadsheet_id, TAB_WEEKLY_SNAPSHOTS),
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True, 'fontSize': 11},
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                }
            },
            # Freeze header row
            {
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': self._get_sheet_id(spreadsheet_id, TAB_WEEKLY_SNAPSHOTS),
                        'gridProperties': {'frozenRowCount': 1}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            }
        ]
        
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        
        print(f"  ✓ {TAB_WEEKLY_SNAPSHOTS} tab configured")
    
    def _setup_chart_data_tab(self, spreadsheet_id: str):
        """Setup Chart_Data tab with table headers"""
        
        # Prepare all table headers
        values = []
        
        # Rating Trend table
        values.append(['iso_week', 'avg_rating'])  # Row 1
        
        # Add empty rows until Review Volume table
        for _ in range(CHART_VOLUME_TREND['start_row'] - len(values) - 1):
            values.append([])
        
        # Review Volume table
        values.append(['iso_week', 'review_count'])
        
        # Sentiment table
        for _ in range(CHART_SENTIMENT['start_row'] - len(values) - 1):
            values.append([])
        values.append(['sentiment', 'count'])
        
        # Rating Distribution table
        for _ in range(CHART_RATING_DIST['start_row'] - len(values) - 1):
            values.append([])
        values.append(['stars', 'count'])
        
        # Negative Themes table
        for _ in range(CHART_NEGATIVE_THEMES['start_row'] - len(values) - 1):
            values.append([])
        values.append(['topic', 'count'])
        
        # Write all headers
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'{TAB_CHART_DATA}!A1',
            valueInputOption='RAW',
            body={'values': values}
        ).execute()
        
        print(f"  ✓ {TAB_CHART_DATA} tab configured")
    
    def _get_sheet_id(self, spreadsheet_id: str, sheet_name: str) -> int:
        """Get internal sheet ID by name"""
        metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        for sheet in metadata['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        raise ValueError(f"Sheet '{sheet_name}' not found")
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """
        Get nested dictionary value by dot-separated path
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "week_stats.sentiment.positive.count")
            
        Returns:
            Value or None if not found
        """
        keys = path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None
        
        return value
    
    def update_weekly_snapshot(self, spreadsheet_id: str, report_data: Dict):
        """
        Update or append weekly snapshot data (idempotent)
        
        Args:
            spreadsheet_id: Google Sheet ID
            report_data: Weekly report JSON data
        """
        iso_week = report_data['report_metadata']['iso_week']
        print(f"\n📊 Updating weekly snapshot: {iso_week}")
        
        # Extract row data from JSON
        row_data = []
        for col in WEEKLY_SNAPSHOT_COLUMNS:
            path = WEEKLY_COLUMN_PATHS.get(col)
            if path:
                value = self._get_nested_value(report_data, path)
                row_data.append(value if value is not None else '')
            else:
                row_data.append('')
        
        # Check if week already exists
        existing = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{TAB_WEEKLY_SNAPSHOTS}!A:A'
        ).execute()
        
        existing_weeks = existing.get('values', [])
        row_index = None
        
        for idx, row in enumerate(existing_weeks[1:], start=2):  # Skip header
            if row and row[0] == iso_week:
                row_index = idx
                break
        
        if row_index:
            # Update existing row
            range_name = f'{TAB_WEEKLY_SNAPSHOTS}!A{row_index}'
            print(f"  ↻ Updating existing row {row_index}")
        else:
            # Append new row
            range_name = f'{TAB_WEEKLY_SNAPSHOTS}!A{len(existing_weeks) + 1}'
            print(f"  ✓ Appending new row {len(existing_weeks) + 1}")
        
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': [row_data]}
        ).execute()
        
        print(f"✅ Weekly snapshot updated")
    
    def update_brand_overview(self, spreadsheet_id: str, report_data: Dict):
        """Update Brand_Overview tab with company metadata"""
        
        company = report_data['company']
        
        rows = [
            ['Brand Name', company['brand_name']],
            ['Business ID', company['business_id']],
            ['Website', company['website']],
            ['Logo URL', company['logo_url']],
            ['Trust Score', company['trust_score']],
            ['Stars', company['stars']],
            ['Total Reviews (All Time)', company['total_reviews_all_time']],
            ['Is Claimed', company['is_claimed']],
            ['Categories', ', '.join(company.get('categories', []))],
            ['AI Summary', company.get('ai_summary', {}).get('summary_text', '') if company.get('ai_summary') else ''],
            ['Top Mentions', ', '.join(company.get('top_mentions_overall', []))],
            ['Last Updated', datetime.now().isoformat()]
        ]
        
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f'{TAB_BRAND_OVERVIEW}!A1',
            valueInputOption='RAW',
            body={'values': rows}
        ).execute()
        
        print(f"✅ Brand overview updated")
    
    def update_chart_data(self, spreadsheet_id: str, report_data: Dict):
        """
        Rebuild Chart_Data tab with latest data
        Overwrites all chart data tables
        """
        print(f"\n📊 Rebuilding chart data...")
        
        # Get all historical weekly data for trends
        snapshots = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{TAB_WEEKLY_SNAPSHOTS}!A2:J1000'  # iso_week, dates, ratings
        ).execute()
        
        snapshot_rows = snapshots.get('values', [])
        
        # Prepare chart data
        updates = []
        
        # 1. Rating Trend (last 100 weeks)
        rating_trend = []
        for row in snapshot_rows[-100:]:  # Last 100 weeks
            if len(row) >= 8:  # Need iso_week and avg_rating
                rating_trend.append([row[0], row[7]])  # iso_week, avg_rating
        
        if rating_trend:
            updates.append({
                'range': f'{TAB_CHART_DATA}!A{CHART_RATING_TREND["start_row"]}',
                'values': rating_trend
            })
        
        # 2. Review Volume Trend (last 100 weeks)
        volume_trend = []
        for row in snapshot_rows[-100:]:
            if len(row) >= 4:  # Need iso_week and total_reviews
                volume_trend.append([row[0], row[3]])  # iso_week, total_reviews
        
        if volume_trend:
            updates.append({
                'range': f'{TAB_CHART_DATA}!A{CHART_VOLUME_TREND["start_row"]}',
                'values': volume_trend
            })
        
        # 3. Sentiment Distribution (current week)
        sentiment_data = [
            ['Positive', report_data['week_stats']['sentiment']['positive']['count']],
            ['Neutral', report_data['week_stats']['sentiment']['neutral']['count']],
            ['Negative', report_data['week_stats']['sentiment']['negative']['count']]
        ]
        updates.append({
            'range': f'{TAB_CHART_DATA}!A{CHART_SENTIMENT["start_row"]}',
            'values': sentiment_data
        })
        
        # 4. Rating Distribution (current week)
        rating_dist = report_data['week_stats']['rating_distribution']
        rating_data = [
            ['5 stars', rating_dist['5_stars']],
            ['4 stars', rating_dist['4_stars']],
            ['3 stars', rating_dist['3_stars']],
            ['2 stars', rating_dist['2_stars']],
            ['1 star', rating_dist['1_star']]
        ]
        updates.append({
            'range': f'{TAB_CHART_DATA}!A{CHART_RATING_DIST["start_row"]}',
            'values': rating_data
        })
        
        # 5. Top Negative Themes (current week)
        negative_themes = report_data['week_stats']['content_analysis']['negative_themes']
        theme_data = [[theme['topic'], theme['count']] for theme in negative_themes[:10]]
        
        if theme_data:
            updates.append({
                'range': f'{TAB_CHART_DATA}!A{CHART_NEGATIVE_THEMES["start_row"]}',
                'values': theme_data
            })
        
        # Batch update all chart data
        if updates:
            body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            
            self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
        
        print(f"✅ Chart data rebuilt ({len(updates)} tables)")
    
    def update_sheet_from_report(self, spreadsheet_id: str, report_data: Dict):
        """
        Main update method - updates all tabs from weekly report
        
        Args:
            spreadsheet_id: Google Sheet ID
            report_data: Weekly report JSON data
        """
        print(f"\n{'='*70}")
        print(f"UPDATING GOOGLE SHEET")
        print(f"{'='*70}")
        
        # Update all tabs
        self.update_brand_overview(spreadsheet_id, report_data)
        self.update_weekly_snapshot(spreadsheet_id, report_data)
        self.update_chart_data(spreadsheet_id, report_data)
        
        print(f"\n{'='*70}")
        print(f"UPDATE COMPLETE")
        print(f"{'='*70}\n")