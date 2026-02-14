#!/usr/bin/env python3
"""
Backfill Historic Data to Google Sheets
Uploads all weeks for all brands with rate limiting
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/mnt/user-data/uploads')

from db import Database
from generate_weekly_report import generate_weekly_report
from sheets.sheets_uploader import DashboardSheetsUploader


def get_all_brands(db):
    """Get all brands from database"""
    return db.query("""
        SELECT id, name, display_name
        FROM companies
        ORDER BY name
    """)


def get_weeks_for_brand(db, company_name):
    """Get all ISO weeks that have data for a brand"""
    result = db.query("""
        SELECT DISTINCT
            TO_CHAR(review_date, 'IYYY-"W"IW') as iso_week,
            MIN(review_date) as week_start
        FROM reviews r
        JOIN companies c ON c.id = r.company_id
        WHERE c.name = %s
        GROUP BY TO_CHAR(review_date, 'IYYY-"W"IW')
        ORDER BY iso_week DESC
    """, (company_name,))
    
    return [r['iso_week'] for r in result]


def get_uploaded_weeks(uploader):
    """Get weeks already uploaded to avoid duplicates"""
    try:
        workbook = uploader.gc.open(uploader.spreadsheet_name)
        raw_data = workbook.worksheet('raw_data')
        
        # Get columns A (iso_week) and D (brand_name)
        values = raw_data.get_all_values()
        
        if len(values) <= 1:  # Only header or empty
            return set()
        
        # Build set of "brand|week" keys
        uploaded = set()
        for row in values[1:]:  # Skip header
            if len(row) >= 4 and row[0] and row[3]:
                iso_week = row[0]
                brand = row[3]
                uploaded.add(f"{brand}|{iso_week}")
        
        return uploaded
        
    except Exception as e:
        print(f"⚠️  Could not check uploaded weeks: {e}")
        return set()


def backfill_all_data(batch_size=50, delay_seconds=1.2):
    """
    Backfill all historic data
    
    Rate limiting optimized for Google Sheets API:
    - 60 requests/minute limit (service account)
    - Using 50 req/min (1.2s delay) to stay safely under
    
    Args:
        batch_size: Number of uploads before longer pause (default: 50 = 1 minute)
        delay_seconds: Delay between uploads (default: 1.2s = 50 req/min)
    """
    
    print("\n" + "="*70)
    print("BACKFILLING HISTORIC DATA TO GOOGLE SHEETS")
    print("="*70 + "\n")
    
    db = Database()
    db.connect()
    
    # Get all brands
    brands = get_all_brands(db)
    print(f"📊 Found {len(brands)} brands\n")
    
    # Initialize uploader
    uploader = DashboardSheetsUploader()
    
    # Check what's already uploaded
    print("🔍 Checking uploaded weeks...")
    uploaded_keys = get_uploaded_weeks(uploader)
    print(f"   Already uploaded: {len(uploaded_keys)} week snapshots\n")
    
    total_uploaded = 0
    total_skipped = 0
    total_failed = 0
    upload_count = 0
    
    for brand in brands:
        brand_name = brand['display_name'] or brand['name']
        domain = brand['name']
        
        print(f"\n{'='*70}")
        print(f"BRAND: {brand_name}")
        print(f"{'='*70}\n")
        
        # Get all weeks for this brand
        weeks = get_weeks_for_brand(db, domain)
        
        if not weeks:
            print(f"⚠️  No data found")
            continue
        
        print(f"📅 Found {len(weeks)} weeks: {weeks[0]} to {weeks[-1]}")
        
        # Filter to missing weeks
        missing_weeks = []
        for week in weeks:
            key = f"{brand_name}|{week}"
            if key not in uploaded_keys:
                missing_weeks.append(week)
        
        if not missing_weeks:
            print(f"✅ All weeks already uploaded")
            total_skipped += len(weeks)
            continue
        
        print(f"📤 Need to upload: {len(missing_weeks)} weeks")
        print(f"⏭️  Skipping: {len(weeks) - len(missing_weeks)} weeks (already uploaded)\n")
        
        # Upload missing weeks
        for week in missing_weeks:
            try:
                # Generate report
                print(f"  📊 {week}...", end=' ', flush=True)
                report = generate_weekly_report(db, domain, week)
                
                if not report:
                    print("❌ No data")
                    total_failed += 1
                    continue
                
                # Upload
                print("uploading...", end=' ', flush=True)
                uploader.append_data_row(
                    uploader.gc.open(uploader.spreadsheet_name).worksheet('raw_data'),
                    report
                )
                
                print("✅")
                total_uploaded += 1
                upload_count += 1
                
                # Rate limiting
                if upload_count % batch_size == 0:
                    print(f"\n  ⏸️  Batch complete ({batch_size} uploads ≈ 1 min) - pausing 5s for quota reset...")
                    time.sleep(5)
                else:
                    time.sleep(delay_seconds)
                
            except Exception as e:
                print(f"❌ {e}")
                total_failed += 1
                time.sleep(delay_seconds)
    
    db.close()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"✅ BACKFILL COMPLETE")
    print(f"{'='*70}")
    print(f"\n📊 Summary:")
    print(f"   ✅ Uploaded: {total_uploaded}")
    print(f"   ⏭️  Skipped: {total_skipped} (already existed)")
    if total_failed:
        print(f"   ❌ Failed: {total_failed}")
    print(f"\n🔗 View spreadsheet:")
    print(f"   https://docs.google.com/spreadsheets/d/{uploader.find_or_create_spreadsheet()}\n")


if __name__ == "__main__":
    # Parse args
    batch = 50
    delay = 1.2
    
    if '--batch' in sys.argv:
        idx = sys.argv.index('--batch')
        if idx + 1 < len(sys.argv):
            batch = int(sys.argv[idx + 1])
    
    if '--delay' in sys.argv:
        idx = sys.argv.index('--delay')
        if idx + 1 < len(sys.argv):
            delay = float(sys.argv[idx + 1])
    
    print(f"⏱️  Rate limiting: {batch} uploads/batch (~1 min), {delay}s between uploads")
    print(f"📊 Throughput: ~{int(60/delay)} requests/minute (limit: 60/min)\n")
    
    try:
        backfill_all_data(batch_size=batch, delay_seconds=delay)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)