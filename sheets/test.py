#!/usr/bin/env python3
"""
Test script for sheets_uploader_v2.py

Demonstrates:
1. Loading a report JSON
2. Uploading to Google Sheets
3. Verifying structure
"""

import sys
import json
from sheets_uploader import SheetsUploader


def test_upload():
    """Test upload with sample report data"""
    
    print("\n" + "="*70)
    print("TESTING SHEETS UPLOADER V2")
    print("="*70 + "\n")
    
    # Sample report file (adjust path as needed)
    report_file = "weekly_report_ketogo_app_2026-W04.json"
    
    try:
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        print(f"✅ Loaded report: {report_file}")
    except FileNotFoundError:
        print(f"❌ Report file not found: {report_file}")
        print("\nGenerate a report first:")
        print("  python generate_weekly_report.py <brand> <iso_week>")
        return False
    
    # Initialize uploader
    try:
        uploader = SheetsUploader()
    except Exception as e:
        print(f"❌ Failed to initialize uploader: {e}")
        print("\nCheck your .env file:")
        print("  GOOGLE_DRIVE_FOLDER_ID=...")
        print("  GOOGLE_SHEETS_CREDENTIALS=...")
        return False
    
    # Upload
    try:
        spreadsheet_id = uploader.upload_report(report_data)
        
        print("\n" + "="*70)
        print("✅ TEST PASSED")
        print("="*70)
        print(f"\n📊 Dashboard URL:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
        print(f"\n✨ What you'll see:")
        print(f"   • raw_data sheet - All metrics in one table")
        print(f"   • dashboard sheet - Interactive selectors + KPIs")
        print(f"   • definitions sheet - Metric explanations")
        print(f"\n🎯 Next steps:")
        print(f"   1. Open the dashboard sheet")
        print(f"   2. Set up data validation on B3 (brands)")
        print(f"   3. Set up data validation on B4 (weeks)")
        print(f"   4. Select a brand + week to see metrics!")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_uploads():
    """Test uploading multiple reports (append-only behavior)"""
    
    print("\n" + "="*70)
    print("TESTING MULTIPLE UPLOADS (APPEND-ONLY)")
    print("="*70 + "\n")
    
    # List of report files to upload
    report_files = [
        "weekly_report_ketogo_app_2026-W04.json",
        "weekly_report_ketogo_app_2026-W05.json",
        "weekly_report_ketogo_app_2026-W06.json",
    ]
    
    uploader = SheetsUploader()
    
    for report_file in report_files:
        try:
            with open(report_file, 'r') as f:
                report_data = json.load(f)
            
            spreadsheet_id = uploader.upload_report(report_data)
            print(f"✅ Uploaded: {report_file}")
            
        except FileNotFoundError:
            print(f"⚠️  Skipped (not found): {report_file}")
        except Exception as e:
            print(f"❌ Failed: {report_file} - {e}")
    
    print("\n✅ Multi-upload test complete")
    print(f"🔗 View dashboard: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "multi":
        # Test multiple uploads
        success = test_multiple_uploads()
    else:
        # Test single upload
        success = test_upload()
    
    sys.exit(0 if success else 1)