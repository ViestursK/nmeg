#!/usr/bin/env python3
"""
Weekly Data - REDESIGNED WITH VERTICAL CARDS
No horizontal scrolling, clear labels, organized sections
"""

from sheets_base import SheetsBase
from decimal import Decimal
import json

class WeeklyDataUploader(SheetsBase):
    """Vertical card-based weekly data"""
    
    def setup_weekly_headers(self, ws):
        """Setup vertical card layout for weekly data"""
        
        # Main section header
        ws.update(values=[['WEEKLY PERFORMANCE TRACKER']], range_name='A15:H15')
        ws.merge_cells('A15:H15')
        ws.format('A15:H15', {
            'textFormat': {'bold': True, 'fontSize': 14, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
            'backgroundColor': {'red': 0.26, 'green': 0.52, 'blue': 0.96},
            'horizontalAlignment': 'CENTER'
        })
        
        # Column headers - organized in logical groups
        headers = [
            # Basic Info
            'Week', 'Dates',
            # Volume Metrics
            'Reviews', 'WoW Δ', 
            # Rating Metrics
            'Avg Rating', 'Rating Δ',
            # Sentiment Split
            'Positive %', 'Negative %'
        ]
        
        ws.update(values=[headers], range_name='A17:H17')
        
        # Header styling
        ws.format('A17:H17', {
            'textFormat': {'bold': True, 'fontSize': 11, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
            'backgroundColor': {'red': 0.4, 'green': 0.4, 'blue': 0.4},
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE',
            'wrapStrategy': 'WRAP'
        })
        
        # Freeze header
        ws.freeze(rows=17)
        
        return ws
    
    def setup_details_section(self, ws):
        """Setup expandable details section (hidden by default)"""
        
        # Details header (row starting after main table)
        details_start = 50  # Adjust based on data
        
        ws.update(values=[['DETAILED BREAKDOWN (EXPAND TO VIEW)']], range_name=f'J15:Q15')
        ws.merge_cells(f'J15:Q15')
        ws.format(f'J15:Q15', {
            'textFormat': {'bold': True, 'fontSize': 12},
            'backgroundColor': {'red': 0.85, 'green': 0.85, 'blue': 0.85},
            'horizontalAlignment': 'CENTER'
        })
        
        # Details columns
        details_headers = [
            'Week',
            # Distribution
            '5⭐', '4⭐', '3⭐', '2⭐', '1⭐',
            # Response
            'Response Rate', 'Avg Response Time',
            # Sources
            'Verified', 'Organic'
        ]
        
        ws.update(values=[details_headers], range_name='J17:S17')
        ws.format('J17:S17', {
            'textFormat': {'bold': True, 'fontSize': 10},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
            'horizontalAlignment': 'CENTER'
        })
        
        return ws
    
    def build_weekly_row(self, report_data):
        """Build main metrics row"""
        
        rm = report_data['report_metadata']
        rv = report_data['week_stats']['review_volume']
        rp = report_data['week_stats']['rating_performance']
        s = report_data['week_stats']['sentiment']
        
        # Format dates nicely
        week_dates = f"{rm['week_start'][5:]} to {rm['week_end'][5:]}"
        
        return [
            rm['iso_week'],
            week_dates,
            rv['total_this_week'],
            rv['wow_change'],
            round(rp['avg_rating_this_week'], 2),
            round(rp.get('wow_change', 0), 2),
            round(s['positive']['percentage'], 1),
            round(s['negative']['percentage'], 1)
        ]
    
    def build_details_row(self, report_data):
        """Build details row"""
        
        rm = report_data['report_metadata']
        rd = report_data['week_stats']['rating_distribution']
        resp = report_data['week_stats']['response_performance']
        rv = report_data['week_stats']['review_volume']
        
        return [
            rm['iso_week'],
            rd['5_stars'],
            rd['4_stars'],
            rd['3_stars'],
            rd['2_stars'],
            rd['1_star'],
            f"{resp['response_rate_pct']:.1f}%",
            f"{resp.get('avg_response_time_days', 0) or 0:.1f}d",
            rv['by_source']['verified_invited'],
            rv['by_source']['organic']
        ]
    
    def apply_row_formatting(self, ws, row_index, row_data):
        """Apply formatting to main metrics row"""
        
        # Alternating rows
        if row_index % 2 == 0:
            bg = {'red': 0.98, 'green': 0.98, 'blue': 0.98}
        else:
            bg = {'red': 1, 'green': 1, 'blue': 1}
        
        ws.format(f'A{row_index}:H{row_index}', {
            'backgroundColor': bg,
            'verticalAlignment': 'MIDDLE',
            'horizontalAlignment': 'CENTER'
        })
        
        # Format rating with color
        rating = row_data[4]
        if rating >= 4.0:
            color = {'red': 0.85, 'green': 0.95, 'blue': 0.85}
        elif rating >= 3.0:
            color = {'red': 1, 'green': 0.95, 'blue': 0.8}
        else:
            color = {'red': 1, 'green': 0.9, 'blue': 0.9}
        
        ws.format(f'E{row_index}', {
            'backgroundColor': color,
            'textFormat': {'bold': True, 'fontSize': 12}
        })
        
        # Format WoW change
        wow = row_data[3]
        if wow > 0:
            ws.format(f'D{row_index}', {
                'backgroundColor': {'red': 0.85, 'green': 0.95, 'blue': 0.85},
                'textFormat': {'foregroundColor': {'red': 0, 'green': 0.5, 'blue': 0}}
            })
        elif wow < 0:
            ws.format(f'D{row_index}', {
                'backgroundColor': {'red': 1, 'green': 0.9, 'blue': 0.9},
                'textFormat': {'foregroundColor': {'red': 0.8, 'green': 0, 'blue': 0}}
            })
        
        # Bold week number
        ws.format(f'A{row_index}', {'textFormat': {'bold': True}})
    
    def apply_details_formatting(self, ws, row_index, row_data):
        """Apply formatting to details row"""
        
        if row_index % 2 == 0:
            bg = {'red': 0.98, 'green': 0.98, 'blue': 0.98}
        else:
            bg = {'red': 1, 'green': 1, 'blue': 1}
        
        ws.format(f'J{row_index}:S{row_index}', {
            'backgroundColor': bg,
            'verticalAlignment': 'MIDDLE',
            'horizontalAlignment': 'CENTER',
            'textFormat': {'fontSize': 10}
        })
    
    def upload_weekly_row(self, brand_name, report_data):
        """Upload single week"""
        
        iso_week = report_data['report_metadata']['iso_week']
        print(f"  📊 {iso_week}...", end=' ', flush=True)
        
        workbook, spreadsheet_id = self.get_workbook()
        ws = self.get_or_create_tab(workbook, brand_name)
        
        # Setup if needed
        if ws.row_count < 18:
            self.setup_weekly_headers(ws)
            self.setup_details_section(ws)
        
        # Build rows
        main_row = self.build_weekly_row(report_data)
        details_row = self.build_details_row(report_data)
        
        # Find existing row
        all_data = ws.get_all_values()
        row_index = None
        
        for idx, row in enumerate(all_data[17:], start=18):
            if row and row[0] == iso_week:
                row_index = idx
                break
        
        if row_index:
            # Update
            ws.update(values=[main_row], range_name=f'A{row_index}:H{row_index}')
            ws.update(values=[details_row], range_name=f'J{row_index}:S{row_index}')
            self.apply_row_formatting(ws, row_index, main_row)
            self.apply_details_formatting(ws, row_index, details_row)
            print(f"✅ Updated")
        else:
            # Append
            ws.append_row(main_row + [''] + details_row)  # Add spacer column
            row_index = len(ws.get_all_values())
            self.apply_row_formatting(ws, row_index, main_row)
            self.apply_details_formatting(ws, row_index, details_row)
            print(f"✅ Added")
        
        return spreadsheet_id
    
    def upload_multiple_weeks(self, brand_name, reports_list):
        """Upload multiple weeks"""
        
        print(f"\n{'='*70}")
        print(f"UPLOADING WEEKLY DATA: {brand_name}")
        print(f"{'='*70}\n")
        
        workbook, spreadsheet_id = self.get_workbook()
        ws = self.get_or_create_tab(workbook, brand_name)
        
        # Setup
        if ws.row_count < 18:
            self.setup_weekly_headers(ws)
            self.setup_details_section(ws)
        
        # Get existing
        all_data = ws.get_all_values()
        existing_weeks = {row[0]: idx for idx, row in enumerate(all_data[17:], start=18) 
                         if row and row[0]}
        
        # Upload each
        for report_data in reports_list:
            iso_week = report_data['report_metadata']['iso_week']
            main_row = self.build_weekly_row(report_data)
            details_row = self.build_details_row(report_data)
            
            if iso_week in existing_weeks:
                row_index = existing_weeks[iso_week]
                ws.update(values=[main_row], range_name=f'A{row_index}:H{row_index}')
                ws.update(values=[details_row], range_name=f'J{row_index}:S{row_index}')
                self.apply_row_formatting(ws, row_index, main_row)
                self.apply_details_formatting(ws, row_index, details_row)
                print(f"  ↻ {iso_week}")
            else:
                ws.append_row(main_row + [''] + details_row)
                row_index = len(ws.get_all_values())
                self.apply_row_formatting(ws, row_index, main_row)
                self.apply_details_formatting(ws, row_index, details_row)
                print(f"  ✓ {iso_week}")
        
        print(f"\n✅ Uploaded {len(reports_list)} weeks")
        print(f"🔗 https://docs.google.com/spreadsheets/d/{spreadsheet_id}\n")
        
        return spreadsheet_id


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print("Usage: python sheets_weekly_redesigned.py <brand_name> <report.json> [...]")
        sys.exit(1)
    
    brand_name = sys.argv[1]
    report_files = sys.argv[2:]
    
    reports = []
    for f in report_files:
        with open(f, 'r') as fp:
            reports.append(json.load(fp))
    
    uploader = WeeklyDataUploader()
    
    if len(reports) == 1:
        uploader.upload_weekly_row(brand_name, reports[0])
    else:
        uploader.upload_multiple_weeks(brand_name, reports)