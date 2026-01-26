#!/usr/bin/env python3
"""
Google Sheets CLI for Trustpilot Brand Reports

Usage:
    python sheets_cli.py create <brand_name>
    python sheets_cli.py update <spreadsheet_id> <report_json_file>
    python sheets_cli.py update-from-db <spreadsheet_id> <company_name> <iso_week>
"""

import sys
import json
import os
sys.path.insert(0, os.path.dirname(__file__))

from sheets_manager import GoogleSheetsManager

def create_sheet(brand_name: str):
    """Create a new Google Sheet for a brand"""
    manager = GoogleSheetsManager()
    spreadsheet_id = manager.create_brand_sheet(brand_name)
    
    print(f"\n🎉 SUCCESS!")
    print(f"📋 Spreadsheet ID: {spreadsheet_id}")
    print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"\n💡 Save this ID for future updates!")
    
    return spreadsheet_id

def update_sheet_from_file(spreadsheet_id: str, report_file: str):
    """Update Google Sheet from JSON report file"""
    
    if not os.path.exists(report_file):
        print(f"❌ Report file not found: {report_file}")
        sys.exit(1)
    
    with open(report_file, 'r', encoding='utf-8') as f:
        report_data = json.load(f)
    
    manager = GoogleSheetsManager()
    manager.update_sheet_from_report(spreadsheet_id, report_data)
    
    print(f"\n🎉 SUCCESS!")
    print(f"🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

def update_sheet_from_db(spreadsheet_id: str, company_name: str, iso_week: str):
    """Update Google Sheet by generating report from database"""
    
    # Import here to avoid circular dependency
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from generate_weekly_report import generate_weekly_report
    
    print(f"\n📊 Generating report from database...")
    print(f"   Company: {company_name}")
    print(f"   Week: {iso_week}")
    
    report_data = generate_weekly_report(company_name, iso_week)
    
    if not report_data:
        print(f"❌ Failed to generate report")
        sys.exit(1)
    
    manager = GoogleSheetsManager()
    manager.update_sheet_from_report(spreadsheet_id, report_data)
    
    print(f"\n🎉 SUCCESS!")
    print(f"🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

def main():
    """Main CLI entry point"""
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'create':
        if len(sys.argv) != 3:
            print("Usage: python sheets_cli.py create <brand_name>")
            sys.exit(1)
        
        brand_name = sys.argv[2]
        create_sheet(brand_name)
    
    elif command == 'update':
        if len(sys.argv) != 4:
            print("Usage: python sheets_cli.py update <spreadsheet_id> <report_json_file>")
            sys.exit(1)
        
        spreadsheet_id = sys.argv[2]
        report_file = sys.argv[3]
        update_sheet_from_file(spreadsheet_id, report_file)
    
    elif command == 'update-from-db':
        if len(sys.argv) != 5:
            print("Usage: python sheets_cli.py update-from-db <spreadsheet_id> <company_name> <iso_week>")
            sys.exit(1)
        
        spreadsheet_id = sys.argv[2]
        company_name = sys.argv[3]
        iso_week = sys.argv[4]
        update_sheet_from_db(spreadsheet_id, company_name, iso_week)
    
    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()