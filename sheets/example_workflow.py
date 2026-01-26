#!/usr/bin/env python3
"""
Complete Workflow Example: Scraping → Database → Report → Google Sheets

This demonstrates the full pipeline from scraping Trustpilot reviews
to updating a Google Sheet with weekly analytics.
"""

import os
import sys

# Add paths for both modules
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def example_workflow():
    """
    Complete workflow from start to finish
    """
    
    print("\n" + "="*70)
    print("COMPLETE WORKFLOW EXAMPLE")
    print("="*70 + "\n")
    
    # Configuration
    COMPANY_DOMAIN = "ketogo.app"
    ISO_WEEK = "2026-W04"
    SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"  # Replace with actual ID
    
    print("📋 Configuration:")
    print(f"   Company: {COMPANY_DOMAIN}")
    print(f"   Week: {ISO_WEEK}")
    print(f"   Sheet: {SPREADSHEET_ID}")
    print()
    
    # =========================================================================
    # PHASE 1: Scrape Reviews (if needed)
    # =========================================================================
    
    print("="*70)
    print("PHASE 1: SCRAPING REVIEWS")
    print("="*70 + "\n")
    
    print("To scrape reviews, run:")
    print(f"  python main.py")
    print()
    print("This will:")
    print("  - Fetch reviews from Trustpilot")
    print("  - Store in PostgreSQL database")
    print("  - Preserve all metadata and AI summaries")
    print()
    print("⏭️  Skipping (assuming data already in DB)...\n")
    
    # =========================================================================
    # PHASE 2: Generate Weekly Report
    # =========================================================================
    
    print("="*70)
    print("PHASE 2: GENERATING WEEKLY REPORT")
    print("="*70 + "\n")
    
    from generate_weekly_report import generate_weekly_report
    
    print(f"📊 Generating report for {COMPANY_DOMAIN}, week {ISO_WEEK}...")
    
    try:
        report_data = generate_weekly_report(COMPANY_DOMAIN, ISO_WEEK)
        
        if not report_data:
            print("❌ Failed to generate report (no data for this week?)")
            return
        
        print("\n✅ Report generated successfully!")
        print(f"   Total reviews: {report_data['week_stats']['review_volume']['total_this_week']}")
        print(f"   Avg rating: {report_data['week_stats']['rating_performance']['avg_rating_this_week']}/5")
        
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. Company data exists in database")
        return
    
    # =========================================================================
    # PHASE 3: Update Google Sheet
    # =========================================================================
    
    print("\n" + "="*70)
    print("PHASE 3: UPDATING GOOGLE SHEET")
    print("="*70 + "\n")
    
    if SPREADSHEET_ID == "YOUR_SPREADSHEET_ID_HERE":
        print("⚠️  Please set a real SPREADSHEET_ID in this script")
        print("\nTo create a new sheet:")
        print("  cd sheets")
        print(f"  python sheets_cli.py create '{COMPANY_DOMAIN}'")
        print("\nThen copy the spreadsheet ID and update this script.")
        return
    
    from sheets_manager import GoogleSheetsManager
    
    try:
        manager = GoogleSheetsManager()
        manager.update_sheet_from_report(SPREADSHEET_ID, report_data)
        
        print(f"\n✅ Google Sheet updated successfully!")
        print(f"🔗 View: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
        
    except Exception as e:
        print(f"\n❌ Error updating sheet: {e}")
        print("\nMake sure:")
        print("  1. Google Sheets API is enabled")
        print("  2. Credentials JSON is configured in .env")
        print("  3. Spreadsheet ID is correct")
        print("  4. Service account has edit access")
        return
    
    # =========================================================================
    # PHASE 4: Summary
    # =========================================================================
    
    print("\n" + "="*70)
    print("WORKFLOW COMPLETE ✅")
    print("="*70 + "\n")
    
    print("What happened:")
    print(f"  ✓ Generated weekly report for {ISO_WEEK}")
    print(f"  ✓ Updated Google Sheet {SPREADSHEET_ID}")
    print(f"  ✓ Added/updated row in Weekly_Snapshots")
    print(f"  ✓ Rebuilt chart data tables")
    print()
    print("Next steps:")
    print("  1. Open the Google Sheet")
    print("  2. Review the Weekly_Snapshots tab")
    print("  3. Check Chart_Data has updated tables")
    print("  4. Create charts manually from Chart_Data (Phase 6 coming later)")
    print()

def show_cli_alternatives():
    """Show equivalent CLI commands"""
    
    print("\n" + "="*70)
    print("CLI ALTERNATIVES")
    print("="*70 + "\n")
    
    print("You can also run this workflow from the command line:\n")
    
    print("# Generate report and update sheet in one command:")
    print("cd sheets")
    print("python sheets_cli.py update-from-db <spreadsheet_id> ketogo.app 2026-W04\n")
    
    print("# Or in two steps:")
    print("python generate_weekly_report.py ketogo.app 2026-W04")
    print("cd sheets")
    print("python sheets_cli.py update <spreadsheet_id> ../weekly_report_ketogo_app_2026-W04.json\n")

if __name__ == "__main__":
    
    # Check if running with --help
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        show_cli_alternatives()
        sys.exit(0)
    
    try:
        example_workflow()
        show_cli_alternatives()
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)