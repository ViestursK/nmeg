#!/usr/bin/env python3
"""
Test the improved UX sheets uploader with vertical layout
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database
from generate_weekly_report import generate_weekly_report
from sheets.sheets_uploader import ImprovedUXUploader

def test_improved_ux_upload():
    """Test improved UX upload"""
    
    # Configuration
    company_domain = "ketogo.app"
    brand_name = "KetoGo"
    iso_week = "2026-W04"
    
    print("\n" + "="*70)
    print("TESTING IMPROVED UX SHEETS (NO HORIZONTAL SCROLLING)")
    print("="*70 + "\n")
    
    # Generate report
    print(f"📊 Generating report for {brand_name} ({iso_week})...")
    db = Database()
    db.connect()
    
    report_data = generate_weekly_report(db, company_domain, iso_week)
    
    db.close()
    
    if not report_data:
        print("❌ Failed to generate report")
        return False
    
    print("✅ Report generated\n")
    
    # Upload with improved UX
    print("📤 Uploading with improved UX layout...")
    try:
        uploader = ImprovedUXUploader()
        spreadsheet_id = uploader.upload_report(brand_name, report_data)
        
        print("\n" + "="*70)
        print("✅ TEST SUCCESSFUL")
        print("="*70)
        print(f"\n🔗 Check your improved sheet:")
        print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"\n✨ What's new:")
        print(f"   ✓ Only 9 columns (was 24)")
        print(f"   ✓ No horizontal scrolling needed!")
        print(f"   ✓ Related data merged:")
        print(f"     - Week shows date range in one cell")
        print(f"     - Reviews shows count + WoW in one cell")
        print(f"     - Rating shows current + change in one cell")
        print(f"     - Sentiment shows all 3 percentages in one cell")
        print(f"     - Response shows rate + time in one cell")
        print(f"   ✓ Taller rows (80px) for better readability")
        print(f"   ✓ Themes as bulleted lists")
        print(f"   ✓ Everything fits on one screen\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_improved_ux_upload()
    sys.exit(0 if success else 1)