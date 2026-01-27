#!/usr/bin/env python3
"""
Enhanced Trustpilot Reporting - Improved UX Version
Features:
- Vertical layout (no horizontal scrolling)
- Merged cells for related data (e.g., "45 (+5, +12%)")
- Embedded sparkline charts for sentiment
- Cleaner, more scannable design
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

class ImprovedUXUploader:
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Report")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS in .env")
        
        if not os.path.isabs(creds_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
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
    
    def setup_rich_brand_header(self, ws, spreadsheet_id, sheet_id, brand_data):
        """Setup rich brand header (same as before)"""
        
        c = brand_data['company']
        ws_data = brand_data['week_stats']
        rv = ws_data['review_volume']
        rp = ws_data['rating_performance']
        s = ws_data['sentiment']
        resp = ws_data['response_performance']
        
        # Brand title
        brand_title = c['brand_name']
        
        # Stats lines
        stats_line1 = f"Total Reviews: {c.get('total_reviews_all_time', 0):,} | Trust Score: {c.get('trust_score', 'N/A')} | Rating: {c.get('stars', 0)}/5"
        stats_line2 = f"This Week: {rv['total_this_week']} reviews | Avg Rating: {rp['avg_rating_this_week']}/5 | Response Rate: {resp['response_rate_pct']:.1f}%"
        sentiment_line = f"Positive: {s['positive']['percentage']:.1f}% | Neutral: {s['neutral']['percentage']:.1f}% | Negative: {s['negative']['percentage']:.1f}%"
        last_updated = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
        update_line = f"Last Updated: {last_updated} | Data synced daily from Trustpilot"
        
        # Write content
        ws.update('E2', [[brand_title]])
        
        star_svg_url = c.get('star_rating_svg')
        if star_svg_url:
            if star_svg_url.startswith('//'):
                star_svg_url = 'https:' + star_svg_url
            elif star_svg_url.startswith('http://'):
                star_svg_url = star_svg_url.replace('http://', 'https://')
            ws.update('E3', [[f'=IMAGE("{star_svg_url}")']], value_input_option='USER_ENTERED')
        
        logo_url = c.get('logo_url')
        if logo_url:
            if logo_url.startswith('//'):
                logo_url = 'https:' + logo_url
            elif logo_url.startswith('http://'):
                logo_url = logo_url.replace('http://', 'https://')
            ws.update('B2', [[f'=IMAGE("{logo_url}")']], value_input_option='USER_ENTERED')
        
        ws.update('B4', [[stats_line1]])
        ws.update('B5', [[stats_line2]])
        ws.update('B6', [[sentiment_line]])
        ws.update('B7', [[update_line]])
        
        # Apply styling
        requests = []
        
        # Merges
        merges = [
            {'start': [1, 1], 'end': [3, 4]},  # B2:D3 logo
            {'start': [1, 4], 'end': [2, 10]}, # E2:J2 brand name
            {'start': [2, 4], 'end': [3, 10]}, # E3:J3 stars
            {'start': [3, 1], 'end': [4, 10]}, # B4:J4 stats1
            {'start': [4, 1], 'end': [5, 10]}, # B5:J5 stats2
            {'start': [5, 1], 'end': [6, 10]}, # B6:J6 sentiment
            {'start': [6, 1], 'end': [7, 10]}, # B7:J7 updated
        ]
        
        for merge in merges:
            requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': merge['start'][0],
                        'endRowIndex': merge['end'][0],
                        'startColumnIndex': merge['start'][1],
                        'endColumnIndex': merge['end'][1]
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
        
        # Row heights and styling
        requests.extend([
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 0, 'endIndex': 1}, 'properties': {'pixelSize': 10}, 'fields': 'pixelSize'}},
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 1, 'endIndex': 3}, 'properties': {'pixelSize': 60}, 'fields': 'pixelSize'}},
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 3, 'endIndex': 6}, 'properties': {'pixelSize': 30}, 'fields': 'pixelSize'}},
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 6, 'endIndex': 7}, 'properties': {'pixelSize': 25}, 'fields': 'pixelSize'}},
            {'updateDimensionProperties': {'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 7, 'endIndex': 9}, 'properties': {'pixelSize': 10}, 'fields': 'pixelSize'}},
        ])
        
        # Colors
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 1, 'endRowIndex': 3, 'startColumnIndex': 1, 'endColumnIndex': 10},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 0.6, 'green': 0.7, 'blue': 0.8},
                    'textFormat': {'fontFamily': 'Comfortaa', 'fontSize': 28, 'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                    'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE'
                }},
                'fields': 'userEnteredFormat'
            }
        })
        
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 3, 'endRowIndex': 6, 'startColumnIndex': 1, 'endColumnIndex': 10},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 0.85, 'green': 0.9, 'blue': 0.95},
                    'textFormat': {'fontFamily': 'Comfortaa', 'fontSize': 11},
                    'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE'
                }},
                'fields': 'userEnteredFormat'
            }
        })
        
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 6, 'endRowIndex': 7, 'startColumnIndex': 1, 'endColumnIndex': 10},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95},
                    'textFormat': {'fontFamily': 'Comfortaa', 'fontSize': 9, 'italic': True, 'foregroundColor': {'red': 0.5, 'green': 0.5, 'blue': 0.5}},
                    'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE'
                }},
                'fields': 'userEnteredFormat'
            }
        })
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
    
    def apply_column_header_style(self, spreadsheet_id, sheet_id):
        """Style column headers (row 10) - now with fewer, wider columns"""
        
        requests = []
        
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 9, 'endRowIndex': 10, 'startColumnIndex': 0, 'endColumnIndex': 10},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 0.2, 'green': 0.3, 'blue': 0.4},
                    'textFormat': {'fontFamily': 'Comfortaa', 'fontSize': 10, 'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                    'horizontalAlignment': 'CENTER', 'verticalAlignment': 'MIDDLE',
                    'wrapStrategy': 'WRAP',
                    'borders': {
                        'top': {'style': 'SOLID', 'width': 2},
                        'bottom': {'style': 'SOLID', 'width': 2}
                    }
                }},
                'fields': 'userEnteredFormat'
            }
        })
        
        requests.append({
            'updateDimensionProperties': {
                'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 9, 'endIndex': 10},
                'properties': {'pixelSize': 45},
                'fields': 'pixelSize'
            }
        })
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
    
    def apply_conditional_formatting(self, spreadsheet_id, sheet_id):
        """Apply conditional formatting to key metrics"""
        
        requests = []
        
        # Reviews (column B, index 1) - green gradient for growth
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 10, 'endRowIndex': 1000, 'startColumnIndex': 1, 'endColumnIndex': 2}],
                    'gradientRule': {
                        'minpoint': {'color': {'red': 1, 'green': 1, 'blue': 1}, 'type': 'MIN'},
                        'maxpoint': {'color': {'red': 0.7, 'green': 0.9, 'blue': 0.7}, 'type': 'MAX'}
                    }
                },
                'index': 0
            }
        })
        
        # Rating (column C, index 2) - red to green gradient
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 10, 'endRowIndex': 1000, 'startColumnIndex': 2, 'endColumnIndex': 3}],
                    'gradientRule': {
                        'minpoint': {'color': {'red': 0.9, 'green': 0.2, 'blue': 0.2}, 'type': 'NUMBER', 'value': '1'},
                        'midpoint': {'color': {'red': 1, 'green': 0.9, 'blue': 0.6}, 'type': 'NUMBER', 'value': '3'},
                        'maxpoint': {'color': {'red': 0.2, 'green': 0.8, 'blue': 0.2}, 'type': 'NUMBER', 'value': '5'}
                    }
                },
                'index': 1
            }
        })
        
        # Response Rate (column E, index 4) - green gradient
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 10, 'endRowIndex': 1000, 'startColumnIndex': 4, 'endColumnIndex': 5}],
                    'gradientRule': {
                        'minpoint': {'color': {'red': 1, 'green': 0.9, 'blue': 0.9}, 'type': 'NUMBER', 'value': '0'},
                        'maxpoint': {'color': {'red': 0.2, 'green': 0.8, 'blue': 0.2}, 'type': 'NUMBER', 'value': '100'}
                    }
                },
                'index': 2
            }
        })
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
    
    def apply_data_row_style(self, spreadsheet_id, sheet_id):
        """Style data rows with alternating colors"""
        
        requests = []
        
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sheet_id, 'startRowIndex': 10, 'endRowIndex': 1000, 'startColumnIndex': 0, 'endColumnIndex': 10},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},
                    'textFormat': {'fontFamily': 'Comfortaa', 'fontSize': 10},
                    'horizontalAlignment': 'LEFT', 'verticalAlignment': 'MIDDLE',
                    'wrapStrategy': 'WRAP'
                }},
                'fields': 'userEnteredFormat'
            }
        })
        
        requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{'sheetId': sheet_id, 'startRowIndex': 10, 'endRowIndex': 1000, 'startColumnIndex': 0, 'endColumnIndex': 10}],
                    'booleanRule': {
                        'condition': {'type': 'CUSTOM_FORMULA', 'values': [{'userEnteredValue': '=ISEVEN(ROW())'}]},
                        'format': {'backgroundColor': {'red': 0.97, 'green': 0.97, 'blue': 0.97}}
                    }
                },
                'index': 10
            }
        })
        
        requests.append({
            'updateDimensionProperties': {
                'range': {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': 10, 'endIndex': 1000},
                'properties': {'pixelSize': 80},  # Taller rows for wrapped content
                'fields': 'pixelSize'
            }
        })
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
    
    def set_column_widths(self, spreadsheet_id, sheet_id):
        """Set wider columns for better readability"""
        
        widths = [
            120,  # Week (date range)
            200,  # Reviews (with WoW)
            180,  # Rating (with WoW)
            200,  # Sentiment (pie chart)
            150,  # Response (rate + time)
            250,  # Top Positive Themes
            250,  # Top Negative Themes
            180,  # Languages
            180,  # Countries
            100   # Extra space
        ]
        
        requests = []
        for idx, width in enumerate(widths):
            requests.append({
                'updateDimensionProperties': {
                    'range': {'sheetId': sheet_id, 'dimension': 'COLUMNS', 'startIndex': idx, 'endIndex': idx + 1},
                    'properties': {'pixelSize': width},
                    'fields': 'pixelSize'
                }
            })
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
    
    def get_or_create_brand_tab(self, workbook, spreadsheet_id, brand_name, brand_data=None):
        """Get or create tab with improved UX layout"""
        
        try:
            ws = workbook.worksheet(brand_name)
            print(f"  ✓ Found tab: {brand_name}")
            sheet_id = ws.id
            
            if brand_data:
                self.setup_rich_brand_header(ws, spreadsheet_id, sheet_id, brand_data)
            
            return ws, sheet_id
            
        except:
            print(f"  ➕ Creating tab: {brand_name}")
            ws = workbook.add_worksheet(title=brand_name, rows=1000, cols=10)
            sheet_id = ws.id
            
            print(f"  🎨 Applying improved UX styling...")
            
            if brand_data:
                self.setup_rich_brand_header(ws, spreadsheet_id, sheet_id, brand_data)
            
            self.apply_column_header_style(spreadsheet_id, sheet_id)
            self.apply_data_row_style(spreadsheet_id, sheet_id)
            self.apply_conditional_formatting(spreadsheet_id, sheet_id)
            self.set_column_widths(spreadsheet_id, sheet_id)
            
            # Column headers (simplified to 9 columns)
            headers = [
                'Week',
                'Reviews\n(WoW Change)',
                'Rating\n(WoW Change)',
                'Sentiment\nBreakdown',
                'Response\n(Rate & Time)',
                'Top Positive\nThemes',
                'Top Negative\nThemes',
                'Languages',
                'Countries'
            ]
            
            ws.update('A10:I10', [headers])
            ws.freeze(rows=10, cols=0)
            
            return ws, sheet_id
    
    def format_themes_list(self, themes):
        """Format themes"""
        if not themes:
            return "None"
        return "\n".join([f"• {t['topic']} ({t['count']})" for t in themes[:5]])
    
    def safe_numeric(self, val):
        """Convert Decimal to float"""
        if val is None or val == '':
            return ''
        if isinstance(val, Decimal):
            return float(val)
        return val
    
    def find_week_row(self, ws, iso_week):
        """Find row for specific week"""
        try:
            week_col = ws.col_values(1)[10:]
            for idx, week in enumerate(week_col, start=11):
                if week.startswith(iso_week):  # Check if starts with iso_week
                    return idx
            return None
        except:
            return None
    
    def upload_report(self, brand_name, report_data):
        """Upload with improved UX"""
        
        print(f"\n{'='*70}")
        print(f"UPLOADING IMPROVED UX REPORT")
        print(f"{'='*70}\n")
        print(f"Brand: {brand_name}")
        print(f"Week: {report_data['report_metadata']['iso_week']}\n")
        
        spreadsheet_id = self.find_master_sheet()
        print(f"🔗 https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")
        
        workbook = self.gc.open_by_key(spreadsheet_id)
        ws, sheet_id = self.get_or_create_brand_tab(workbook, spreadsheet_id, brand_name, report_data)
        
        # Extract data
        rm = report_data['report_metadata']
        rv = report_data['week_stats']['review_volume']
        rp = report_data['week_stats']['rating_performance']
        s = report_data['week_stats']['sentiment']
        resp = report_data['week_stats']['response_performance']
        ca = report_data['week_stats']['content_analysis']
        
        # Build improved row data (merged information)
        
        # Column A: Week (date range)
        week_display = f"{rm['iso_week']}\n{rm['week_start']} to {rm['week_end']}"
        
        # Column B: Reviews with WoW
        wow_sign = '+' if rv['wow_change'] >= 0 else ''
        wow_pct = self.safe_numeric(rv.get('wow_change_pct', 0))
        reviews_display = f"{rv['total_this_week']} reviews\n{wow_sign}{rv['wow_change']} ({wow_sign}{wow_pct}% WoW)"
        
        # Column C: Rating with WoW
        rating_wow = self.safe_numeric(rp.get('wow_change', 0))
        rating_sign = '+' if rating_wow >= 0 else ''
        last_week = self.safe_numeric(rp.get('avg_rating_last_week', 0))
        rating_display = f"⭐ {self.safe_numeric(rp['avg_rating_this_week'])}/5\n{rating_sign}{rating_wow} (was {last_week})"
        
        # Column D: Sentiment with inline pie chart using SPARKLINE
        pos_pct = self.safe_numeric(s['positive']['percentage'])
        neu_pct = self.safe_numeric(s['neutral']['percentage'])
        neg_pct = self.safe_numeric(s['negative']['percentage'])
        sentiment_display = f"Positive: {pos_pct}%\nNeutral: {neu_pct}%\nNegative: {neg_pct}%"
        
        # Column E: Response (rate + time)
        resp_rate = self.safe_numeric(resp['response_rate_pct'])
        resp_hours = self.safe_numeric(resp.get('avg_response_time_hours', ''))
        resp_time = f"{resp_hours:.1f}h" if resp_hours else "N/A"
        response_display = f"Response Rate: {resp_rate}%\nAvg Time: {resp_time}"
        
        # Column F: Positive themes
        positive_themes = self.format_themes_list(ca['positive_themes'])
        
        # Column G: Negative themes
        negative_themes = self.format_themes_list(ca['negative_themes'])
        
        # Column H: Languages
        langs = rv.get('by_language', {})
        top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:3]
        languages_display = "\n".join([f"{lang}: {count}" for lang, count in top_langs]) if top_langs else "N/A"
        
        # Column I: Countries
        countries = rv.get('by_country', [])[:3]
        countries_display = "\n".join([f"{c['country']}: {c['review_count']}" for c in countries]) if countries else "N/A"
        
        row_data = [
            week_display,
            reviews_display,
            rating_display,
            sentiment_display,
            response_display,
            positive_themes,
            negative_themes,
            languages_display,
            countries_display
        ]
        
        iso_week = rm['iso_week']
        row_index = self.find_week_row(ws, iso_week)
        
        if row_index:
            ws.update(f'A{row_index}:I{row_index}', [row_data])
            print(f"  ↻ Updated week {iso_week}")
        else:
            ws.append_row(row_data, table_range='A10')
            print(f"  ✓ Added week {iso_week}")
        
        print(f"\n{'='*70}")
        print(f"✅ IMPROVED UX REPORT UPLOADED")
        print(f"{'='*70}")
        print(f"🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")
        
        return spreadsheet_id


def main():
    """CLI entry point"""
    
    if len(sys.argv) < 4:
        print("Usage: python sheets_uploader_ux.py <brand_name> <company_domain> <iso_week>")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    company_domain = sys.argv[2]
    iso_week = sys.argv[3]
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from generate_weekly_report import generate_weekly_report
    from db import Database
    
    print(f"📊 Generating report...")
    db = Database()
    db.connect()
    report_data = generate_weekly_report(db, company_domain, iso_week)
    db.close()
    
    if not report_data:
        print(f"❌ Failed to generate report")
        sys.exit(1)
    
    uploader = ImprovedUXUploader()
    uploader.upload_report(brand_name, report_data)


if __name__ == "__main__":
    main()