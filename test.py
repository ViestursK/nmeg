#!/usr/bin/env python3
"""
Test script for SheetsUploaderV3
Tests the new dashboard design with HTML report structure
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database
from generate_weekly_report import generate_weekly_report
from sheets.sheets_uploader import SheetsUploaderV3


def test_v3_upload(company_domain="ketogo.app", iso_week="2026-W04"):
    """Test the V3 uploader with HTML-style dashboard"""
    
    print("\n" + "="*70)
    print("TESTING SHEETS UPLOADER V3")
    print("HTML Report Structure in Google Sheets")
    print("="*70 + "\n")
    
    # Generate report
    print(f"📊 Generating report for {company_domain} ({iso_week})...")
    db = Database()
    db.connect()
    
    report_data = generate_weekly_report(db, company_domain, iso_week)
    
    db.close()
    
    if not report_data:
        print("❌ Failed to generate report")
        return False
    
    print("✅ Report generated\n")
    
    # Upload with V3
    print("📤 Uploading with V3 dashboard...")
    try:
        uploader = SheetsUploaderV3()
        spreadsheet_id = uploader.upload_report(report_data)
        
        print("\n" + "="*70)
        print("✅ TEST SUCCESSFUL")
        print("="*70)
        print(f"\n🔗 Open your report:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"\n✨ What you'll see:")
        print(f"   • raw_data sheet - All data including full AI summary & topics")
        print(f"   • dashboard sheet - Visual report like old HTML design")
        print(f"     - Brand & Week dropdowns at top")
        print(f"     - Company Overview section")
        print(f"     - AI Summary section")
        print(f"     - Top Mentions section")
        print(f"     - Key Metrics section")
        print(f"\n📋 Setup steps (one-time):")
        print(f"   1. Open dashboard sheet")
        print(f"   2. Click cell B3 → Data > Data validation → List from range")
        print(f"      Enter: raw_data!F2:F")
        print(f"   3. Click cell B4 → Data > Data validation → List from range")
        print(f"      Enter: raw_data!B2:B")
        print(f"   4. Now select brand + week to see the report!\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Parse command line args
    company = sys.argv[1] if len(sys.argv) > 1 else "ketogo.app"
    week = sys.argv[2] if len(sys.argv) > 2 else "2026-W04"
    
    success = test_v3_upload(company, week)
    sys.exit(0 if success else 1)