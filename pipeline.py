#!/usr/bin/env python3
"""
Automated Trustpilot Pipeline
- Reads brand list from config
- Scrapes all brands (full history if new, incremental if exists)
- Generates weekly reports directly from DB
- Uploads to Google Sheets (streaming, no large JSON in memory)
- Keeps snapshots ordered with latest on top
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database
from scraper import TrustpilotScraper
from generate_weekly_report import generate_weekly_report

# Only import sheets uploader if needed
try:
    from sheets.sheets_uploader import UnifiedSheetsUploader
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    print("⚠️  Google Sheets integration not available")

load_dotenv()


class TrustpilotPipeline:
    def __init__(self):
        # Single DB connection for entire pipeline
        self.db = Database()
        self.db.connect()  # Connect once
        
        self.scraper = TrustpilotScraper(self.db)
        self.sheets_uploader = UnifiedSheetsUploader() if SHEETS_AVAILABLE else None
        
        # Load brands from config
        self.brands = self.load_brands_config()
        
        print(f"✅ Pipeline initialized with {len(self.brands)} brands")
    
    def __del__(self):
        """Cleanup - close DB connection"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def load_brands_config(self):
        """Load brands from JSON config file or env variable"""
        
        # Try JSON config file first
        config_file = os.getenv("BRANDS_CONFIG", "brands_config.json")
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                brands = config.get('brands', [])
                print(f"📋 Loaded {len(brands)} brands from {config_file}")
                return brands
        
        # Fall back to env variable (comma-separated)
        brands_env = os.getenv("BRANDS_LIST", "")
        if brands_env:
            brands = []
            for item in brands_env.split(','):
                item = item.strip()
                if '|' in item:
                    domain, name = item.split('|')
                    brands.append({'domain': domain.strip(), 'name': name.strip()})
                else:
                    brands.append({'domain': item, 'name': item})
            
            print(f"📋 Loaded {len(brands)} brands from BRANDS_LIST env var")
            return brands
        
        raise ValueError(
            "No brands configured. Either:\n"
            "  1. Create brands_config.json with format:\n"
            '     {"brands": [{"domain": "ketogo.app", "name": "KetoGo"}]}\n'
            "  2. Or set BRANDS_LIST env variable:\n"
            "     BRANDS_LIST=ketogo.app|KetoGo,simple-life-app.com|Simple Life App"
        )
    
    def get_brand_metadata(self, domain):
        """
        Get brand metadata in single query:
        - company_id (or None if doesn't exist)
        - latest review date
        - total reviews
        """
        result = self.db.query("""
            SELECT 
                c.id,
                MAX(r.review_date) as latest_date,
                COUNT(r.id) as review_count
            FROM companies c
            LEFT JOIN reviews r ON r.company_id = c.id
            WHERE c.name = %s
            GROUP BY c.id
        """, (domain,))
        
        if not result or not result[0]['id']:
            return None
        
        return result[0]
    
    def calculate_weeks_from_latest(self, latest_date, weeks_back):
        """Calculate ISO weeks efficiently from latest date"""
        if not latest_date:
            return []
        
        weeks = []
        year, week, _ = latest_date.isocalendar()
        
        for i in range(weeks_back):
            current_week = week - i
            current_year = year
            
            # Handle year rollover
            if current_week <= 0:
                current_year -= 1
                # Get last week of previous year
                last_day = datetime(current_year, 12, 28)
                _, weeks_in_year, _ = last_day.isocalendar()
                current_week = weeks_in_year + current_week
            
            iso_week = f"{current_year}-W{current_week:02d}"
            weeks.append(iso_week)
        
        return weeks
    
    def scrape_brand(self, brand):
        """Scrape a single brand"""
        
        domain = brand['domain']
        name = brand['name']
        
        print(f"\n{'='*70}")
        print(f"SCRAPING: {name}")
        print(f"{'='*70}\n")
        
        # Get brand metadata (single query)
        metadata = self.get_brand_metadata(domain)
        exists = metadata is not None
        
        if exists:
            print(f"📊 Brand exists ({metadata['review_count']} reviews) - incremental scrape (last 30 days)")
            self.scraper.scrape_and_save(domain, use_date_filter=True, batch_size=20)
        else:
            print(f"📥 New brand - full historical scrape")
            self.scraper.scrape_and_save(domain, use_date_filter=False, batch_size=20)
        
        print(f"✅ Scraping complete for {name}\n")
    
    def generate_and_upload_report(self, brand, iso_week):
        """Generate report from DB and upload to sheets (streaming, no large JSON)"""
        
        domain = brand['domain']
        name = brand['name']
        
        # Generate report using shared DB connection (new signature: db, company, week)
        report_data = generate_weekly_report(self.db, domain, iso_week)
        
        if not report_data:
            return False
        
        # Upload to sheets if available
        if self.sheets_uploader:
            try:
                self.sheets_uploader.upload_report(name, report_data)
            except Exception as e:
                print(f"  ❌ Upload failed: {e}")
                # Debug: print which field has the issue
                import traceback
                traceback.print_exc()
                return False
        
        # Clear report_data from memory immediately
        del report_data
        
        return True
    
    def process_brand_reports(self, brand, weeks_back=4, batch_size=20):
        """
        Generate and upload reports for recent weeks
        Process in batches to handle large week counts (e.g., 167 weeks)
        Uses optimized single-query metadata fetch
        """
        
        domain = brand['domain']
        name = brand['name']
        
        print(f"\n{'='*70}")
        print(f"GENERATING REPORTS: {name}")
        print(f"{'='*70}\n")
        
        # Get brand metadata (single query - much faster!)
        metadata = self.get_brand_metadata(domain)
        
        if not metadata or not metadata['latest_date']:
            print(f"⚠️  No reviews found for {name}")
            return
        
        # Calculate weeks efficiently (no DB queries)
        weeks = self.calculate_weeks_from_latest(metadata['latest_date'], weeks_back)
        
        if not weeks:
            print(f"⚠️  No weeks to report for {name}")
            return
        
        print(f"📅 Found {len(weeks)} weeks to report: {weeks[0]} to {weeks[-1]}")
        print(f"📊 Brand has {metadata['review_count']} total reviews")
        
        if len(weeks) > 50:
            print(f"⚠️  Large dataset ({len(weeks)} weeks) - processing in batches of {batch_size}\n")
        else:
            print()
        
        # Process in batches
        total_uploaded = 0
        failed = 0
        
        for i in range(0, len(weeks), batch_size):
            batch = weeks[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(weeks) + batch_size - 1) // batch_size
            
            if len(weeks) > batch_size:
                print(f"📦 Batch {batch_num}/{total_batches}: {batch[0]} to {batch[-1]}")
            
            for iso_week in batch:
                if self.generate_and_upload_report(brand, iso_week):
                    total_uploaded += 1
                else:
                    failed += 1
            
            if len(weeks) > batch_size:
                print(f"  ✓ Batch complete: {len(batch)} weeks processed\n")
        
        print(f"📊 Summary for {name}:")
        print(f"  ✅ Uploaded: {total_uploaded}")
        if failed > 0:
            print(f"  ❌ Failed: {failed}")
        
        # Only sort if we actually uploaded data
        if total_uploaded > 0:
            self.ensure_sheets_order(brand['name'])
    
    def ensure_sheets_order(self, brand_name):
        """Ensure sheet rows are ordered with latest week on top using Sheets API sort"""
        
        if not self.sheets_uploader:
            return
        
        print(f"\n  🔄 Sorting {brand_name} sheet (latest on top)...")
        
        try:
            spreadsheet_id = self.sheets_uploader.find_master_sheet()
            
            # Get sheet ID
            sheet_metadata = self.sheets_uploader.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in sheet_metadata['sheets']:
                if sheet['properties']['title'] == brand_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if not sheet_id:
                print(f"  ⚠️  Sheet {brand_name} not found")
                return
            
            # Use Sheets API sort request (no data transfer!)
            sort_request = {
                'sortRange': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,  # Skip header
                    },
                    'sortSpecs': [{
                        'dimensionIndex': 0,  # Column A (iso_week)
                        'sortOrder': 'DESCENDING'
                    }]
                }
            }
            
            self.sheets_uploader.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': [sort_request]}
            ).execute()
            
            print(f"  ✅ Sorted via API (zero data transfer)")
            
        except Exception as e:
            print(f"  ⚠️  Sort failed: {e}")
    
    def run_full_pipeline(self, scrape=True, report=True, weeks_back=4):
        """Run complete pipeline for all brands"""
        
        print(f"\n{'='*70}")
        print(f"STARTING FULL PIPELINE")
        print(f"{'='*70}")
        print(f"Brands: {len(self.brands)}")
        print(f"Scrape: {scrape}")
        print(f"Report: {report}")
        print(f"Weeks back: {weeks_back}")
        print(f"{'='*70}\n")
        
        for brand in self.brands:
            try:
                # Step 1: Scrape
                if scrape:
                    self.scrape_brand(brand)
                
                # Step 2: Generate reports and upload
                if report:
                    self.process_brand_reports(brand, weeks_back)
                
            except Exception as e:
                print(f"\n❌ Error processing {brand['name']}: {e}\n")
                continue
        
        print(f"\n{'='*70}")
        print(f"✅ PIPELINE COMPLETE")
        print(f"{'='*70}\n")


def main():
    """CLI entry point"""
    
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        print("\nUsage:")
        print("  python pipeline.py                    # Run full pipeline (scrape + report)")
        print("  python pipeline.py --scrape-only      # Only scrape reviews")
        print("  python pipeline.py --report-only      # Only generate reports")
        print("  python pipeline.py --weeks 8          # Report last 8 weeks")
        print("")
        print("Configuration:")
        print("  Create brands_config.json:")
        print('    {"brands": [')
        print('      {"domain": "ketogo.app", "name": "KetoGo"},')
        print('      {"domain": "simple-life-app.com", "name": "Simple Life App"}')
        print('    ]}')
        print("")
        print("  Or set BRANDS_LIST environment variable:")
        print("    BRANDS_LIST=ketogo.app|KetoGo,simple-life-app.com|Simple Life App")
        sys.exit(0)
    
    # Parse arguments
    scrape = True
    report = True
    weeks_back = 4
    
    if '--scrape-only' in sys.argv:
        report = False
    
    if '--report-only' in sys.argv:
        scrape = False
    
    if '--weeks' in sys.argv:
        idx = sys.argv.index('--weeks')
        if idx + 1 < len(sys.argv):
            weeks_back = int(sys.argv[idx + 1])
    
    # Run pipeline
    try:
        pipeline = TrustpilotPipeline()
        pipeline.run_full_pipeline(scrape=scrape, report=report, weeks_back=weeks_back)
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()