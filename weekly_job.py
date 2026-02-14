#!/usr/bin/env python3
"""
Weekly Trustpilot Job
- Run Monday 00:00 for weekly reports
- One-time backfill mode for historical data
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

from db import Database
from scraper import TrustpilotScraper
from generate_weekly_report import generate_weekly_report
from sheets.sheets_uploader import DashboardSheetsUploader

load_dotenv()


def get_last_completed_week():
    """Get ISO week that just ended (for Monday 00:00 run)"""
    today = datetime.now()
    
    # If today is Monday, last week just ended
    # Otherwise get the most recent completed week
    last_sunday = today - timedelta(days=today.weekday() + 1)
    
    year, week, _ = last_sunday.isocalendar()
    return f"{year}-W{week:02d}"


def get_all_weeks_from_db(db, brand_domain):
    """Get all ISO weeks that have reviews in DB"""
    result = db.query("""
        SELECT DISTINCT 
            TO_CHAR(DATE_TRUNC('week', review_date), 'IYYY-"W"IW') as iso_week,
            COUNT(*) as review_count
        FROM reviews r
        JOIN companies c ON r.company_id = c.id
        WHERE c.name = %s
        GROUP BY iso_week
        ORDER BY iso_week DESC
    """, (brand_domain,))
    
    return [row['iso_week'] for row in result]


def scrape_brand(db, brand):
    """Scrape one brand (incremental 30 days)"""
    print(f"\n{'='*70}")
    print(f"SCRAPING: {brand['name']}")
    print(f"{'='*70}\n")
    
    scraper = TrustpilotScraper(db)
    scraper.scrape_and_save(brand['domain'], use_date_filter=True, batch_size=50)
    
    print(f"✅ Scraping complete\n")


def weekly_mode(brands):
    """Normal weekly run - scrape + upload last week only"""
    
    print(f"\n{'='*70}")
    print(f"WEEKLY MODE - Last Completed Week")
    print(f"{'='*70}\n")
    
    # Calculate last completed week
    last_week = get_last_completed_week()
    print(f"📅 Target week: {last_week}\n")
    
    # Initialize
    db = Database()
    db.connect()
    uploader = DashboardSheetsUploader()
    
    spreadsheet_id = uploader.find_or_create_spreadsheet()
    workbook = uploader.gc.open_by_key(spreadsheet_id)
    
    # Process each brand
    for brand in brands:
        print(f"\n{'─'*70}")
        print(f"BRAND: {brand['name']}")
        print(f"{'─'*70}\n")
        
        try:
            # 1. Scrape (last 30 days)
            scrape_brand(db, brand)
            
            # 2. Upload last week only
            print(f"📤 Uploading weekly report:")
            
            # Prepare upload objects
            spreadsheet_id = uploader.find_or_create_spreadsheet()
            workbook = uploader.gc.open_by_key(spreadsheet_id)
            raw_data_ws = uploader.setup_raw_data_sheet(workbook)
            existing = uploader.get_existing_data(raw_data_ws)
            
            # Check if exists
            key = f"{brand['name']}|{last_week}"
            if key in existing:
                print(f"  ⏭️  {last_week} - already uploaded, skipping")
            else:
                # Generate report
                print(f"  📊 {last_week} - generating...", end=' ')
                report_data = generate_weekly_report(db, brand['domain'], last_week)
                
                if not report_data:
                    print("❌ no data")
                else:
                    # Upload
                    print(f"uploading...", end=' ')
                    try:
                        uploader.upload_report(
                            brand['name'],
                            report_data,
                            workbook=workbook,
                            raw_data_ws=raw_data_ws,
                            existing=existing
                        )
                        print("✅")
                    except Exception as e:
                        print(f"❌ {e}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue
    
    db.close()
    
    print(f"\n{'='*70}")
    print(f"✅ WEEKLY JOB COMPLETE")
    print(f"{'='*70}\n")


def backfill_mode(brands, weeks_limit=None):
    """One-time backfill - scrape + upload ALL historical weeks"""
    
    print(f"\n{'='*70}")
    print(f"BACKFILL MODE - All Historical Weeks")
    print(f"{'='*70}\n")
    
    if weeks_limit:
        print(f"⚠️  Limited to last {weeks_limit} weeks\n")
    
    # Initialize
    db = Database()
    db.connect()
    uploader = DashboardSheetsUploader()
    
    spreadsheet_id = uploader.find_or_create_spreadsheet()
    workbook = uploader.gc.open_by_key(spreadsheet_id)
    
    # Process each brand
    for brand in brands:
        print(f"\n{'─'*70}")
        print(f"BRAND: {brand['name']}")
        print(f"{'─'*70}\n")
        
        try:
            # 1. Full scrape (no date filter) - only on first run
            metadata = db.query(
                "SELECT COUNT(*) as count FROM reviews r JOIN companies c ON r.company_id = c.id WHERE c.name = %s",
                (brand['domain'],)
            )
            
            if metadata[0]['count'] == 0:
                print("📥 First run - full historical scrape\n")
                scraper = TrustpilotScraper(db)
                scraper.scrape_and_save(brand['domain'], use_date_filter=False, batch_size=100)
            else:
                print("📊 Reviews exist - incremental scrape\n")
                scrape_brand(db, brand)
            
            # 2. Get all weeks from DB
            all_weeks = get_all_weeks_from_db(db, brand['domain'])
            
            if weeks_limit:
                all_weeks = all_weeks[:weeks_limit]
            
            print(f"\n📤 Uploading {len(all_weeks)} weeks:\n")
            
            # 3. Upload all weeks with batching to avoid rate limits
            uploaded = 0
            skipped = 0
            failed = 0
            
            # Fetch workbook/sheet once for the whole brand
            spreadsheet_id = uploader.find_or_create_spreadsheet()
            workbook = uploader.gc.open_by_key(spreadsheet_id)
            raw_data_ws = uploader.setup_raw_data_sheet(workbook)
            existing = uploader.get_existing_data(raw_data_ws)
            
            import time
            for idx, iso_week in enumerate(all_weeks):
                # Rate limiting: max 50 uploads per minute
                if idx > 0 and idx % 50 == 0:
                    print(f"\n  ⏸️  Rate limit pause (50 uploads) - waiting 60s...\n")
                    time.sleep(60)
                    # Refresh existing data after pause
                    existing = uploader.get_existing_data(raw_data_ws)
                
                # Check if exists
                key = f"{brand['name']}|{iso_week}"
                if key in existing:
                    print(f"  ⏭️  {iso_week} - already uploaded, skipping")
                    skipped += 1
                    continue
                
                # Generate report
                print(f"  📊 {iso_week} - generating...", end=' ')
                report_data = generate_weekly_report(db, brand['domain'], iso_week)
                
                if not report_data:
                    print("❌ no data")
                    failed += 1
                    continue
                
                # Upload with reused objects
                print(f"uploading...", end=' ')
                try:
                    result = uploader.upload_report(
                        brand['name'], 
                        report_data,
                        workbook=workbook,
                        raw_data_ws=raw_data_ws,
                        existing=existing
                    )
                    # Update cache with new entry
                    existing = result['existing']
                    print("✅")
                    uploaded += 1
                except Exception as e:
                    print(f"❌ {e}")
                    failed += 1
            
            print(f"\n📊 Summary:")
            print(f"  ✅ Uploaded: {uploaded}")
            print(f"  ⏭️  Skipped: {skipped}")
            if failed > 0:
                print(f"  ❌ Failed: {failed}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
            continue
    
    db.close()
    
    print(f"\n{'='*70}")
    print(f"✅ BACKFILL COMPLETE")
    print(f"{'='*70}\n")


def main():
    """CLI entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Weekly Trustpilot Job - Scrape and Report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal weekly run (for cron - runs last week)
  python weekly_job.py
  
  # One-time backfill (all historical weeks)
  python weekly_job.py --backfill
  
  # Backfill limited to last 10 weeks
  python weekly_job.py --backfill --weeks 10
  
  # Test with specific week
  python weekly_job.py --week 2026-W06
  
  # Test backfill with custom config
  python weekly_job.py --backfill --config my_brands.json
        """
    )
    
    parser.add_argument(
        '--backfill',
        action='store_true',
        help='Backfill mode: upload all historical weeks'
    )
    
    parser.add_argument(
        '--week',
        type=str,
        help='Test mode: upload specific week (e.g., 2026-W06)'
    )
    
    parser.add_argument(
        '--weeks',
        type=int,
        help='Limit backfill to last N weeks'
    )
    
    parser.add_argument(
        '--config',
        default='brands_config.json',
        help='Brands config file (default: brands_config.json)'
    )
    
    args = parser.parse_args()
    
    # Load brands
    if not os.path.exists(args.config):
        print(f"❌ Config file not found: {args.config}")
        sys.exit(1)
    
    with open(args.config, 'r') as f:
        config = json.load(f)
        brands = config.get('brands', [])
    
    if not brands:
        print("❌ No brands in config")
        sys.exit(1)
    
    print(f"📋 Loaded {len(brands)} brands from {args.config}")
    
    # Route to correct mode
    if args.week:
        # Test specific week
        print(f"\n{'='*70}")
        print(f"TEST MODE - Specific Week: {args.week}")
        print(f"{'='*70}\n")
        
        db = Database()
        db.connect()
        uploader = DashboardSheetsUploader()
        spreadsheet_id = uploader.find_or_create_spreadsheet()
        workbook = uploader.gc.open_by_key(spreadsheet_id)
        raw_data_ws = uploader.setup_raw_data_sheet(workbook)
        existing = uploader.get_existing_data(raw_data_ws)
        
        for brand in brands:
            print(f"\n{brand['name']}:")
            print(f"  📊 {args.week} - generating...", end=' ')
            report_data = generate_weekly_report(db, brand['domain'], args.week)
            
            if not report_data:
                print("❌ no data")
                continue
            
            print(f"uploading...", end=' ')
            try:
                uploader.upload_report(
                    brand['name'],
                    report_data,
                    workbook=workbook,
                    raw_data_ws=raw_data_ws,
                    existing=existing
                )
                print("✅")
            except Exception as e:
                print(f"❌ {e}")
        
        db.close()
        
    elif args.backfill:
        # Backfill all historical
        backfill_mode(brands, weeks_limit=args.weeks)
        
    else:
        # Normal weekly run
        weekly_mode(brands)


if __name__ == "__main__":
    main()