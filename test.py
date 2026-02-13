#!/usr/bin/env python3
"""
Test Sheet Upload - Single Week
"""

import sys
import os

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from uploaded files
sys.path.insert(0, '/mnt/user-data/uploads')

from db import Database
from generate_weekly_report import generate_weekly_report
from sheets.sheets_uploader import DashboardSheetsUploader


def test_upload(company_domain="ketogo.app", iso_week="2026-W04"):
    """Test the simplified sheet upload"""
    
    print("\n" + "="*70)
    print("TESTING SHEET UPLOAD")
    print("="*70 + "\n")
    
    # 1. Generate report
    print(f"📊 Generating report: {company_domain} | {iso_week}")
    db = Database()
    db.connect()
    
    report_data = generate_weekly_report(db, company_domain, iso_week)
    db.close()
    
    if not report_data:
        print("❌ No report generated")
        return False
    
    print(f"✅ Report generated ({report_data['total_reviews']} reviews)\n")
    
    # 2. Upload to sheets
    print("📤 Uploading to Google Sheets...")
    try:
        uploader = DashboardSheetsUploader()
        spreadsheet_id = uploader.upload_report(
            report_data['brand_name'], 
            report_data
        )
        
        print("\n" + "="*70)
        print("✅ TEST SUCCESSFUL")
        print("="*70)
        print(f"\n🔗 View: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"\n📊 What's uploaded:")
        print(f"   • {report_data['brand_name']}")
        print(f"   • {iso_week}")
        print(f"   • {report_data['total_reviews']} reviews")
        print(f"   • Avg rating: {report_data['avg_rating']}/5")
        print(f"\n💡 Check the 'raw_data' sheet\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Parse args
    company = sys.argv[1] if len(sys.argv) > 1 else "ketogo.app"
    week = sys.argv[2] if len(sys.argv) > 2 else "2026-W00"
    
    success = test_upload(company, week)
    sys.exit(0 if success else 1)