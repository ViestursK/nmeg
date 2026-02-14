#!/usr/bin/env python3
"""
Automated Trustpilot Pipeline with Dashboard
- Scrapes all brands
- Generates weekly reports
- Uploads to Google Sheets with interactive dashboard
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

# Import dashboard uploader
SHEETS_AVAILABLE = False
sheets_uploader_class = None

print("🔍 Looking for sheets uploader...")

try:
    from sheets.sheets_uploader import DashboardSheetsUploader
    sheets_uploader_class = DashboardSheetsUploader
    SHEETS_AVAILABLE = True
    print("✅ Found: sheets/sheets_uploader.py with DashboardSheetsUploader")
except ImportError as e:
    print(f"❌ Could not import DashboardSheetsUploader: {e}")
    print("   Check that sheets/sheets_uploader.py has the DashboardSheetsUploader class")

load_dotenv()


class TrustpilotPipeline:
    def __init__(self):
        # Single DB connection for entire pipeline
        self.db = Database()
        self.db.connect()
        
        self.scraper = TrustpilotScraper(self.db)
        self.sheets_uploader = sheets_uploader_class() if SHEETS_AVAILABLE else None
        
        if self.sheets_uploader:
            print(f"✅ Sheets uploader: {sheets_uploader_class.__name__}")
        else:
            print("⚠️  Sheets uploader: None (uploads disabled)")
        
        # Load brands from config
        self.brands = self.load_brands_config()
        
        print(f"✅ Pipeline initialized with {len(self.brands)} brands")
    
    def __del__(self):
        """Cleanup - close DB connection"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def load_brands_config(self):
        """Load brands from JSON config file or env variable"""
        
        config_file = os.getenv("BRANDS_CONFIG", "brands_config.json")
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                brands = config.get('brands', [])
                print(f"📋 Loaded {len(brands)} brands from {config_file}")
                return brands
        
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
            "  2. Or set BRANDS_LIST env variable"
        )
    
    def get_brand_metadata(self, domain):
        """Get brand metadata in single query"""
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
            
            if current_week <= 0:
                current_year -= 1
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
        
        metadata = self.get_brand_metadata(domain)
        exists = metadata is not None
        
        if exists:
            print(f"📊 Brand exists ({metadata['review_count']} reviews) - incremental scrape")
            self.scraper.scrape_and_save(domain, use_date_filter=True, batch_size=50)
        else:
            print(f"📥 New brand - full historical scrape")
            self.scraper.scrape_and_save(domain, use_date_filter=False, batch_size=100)
        
        print(f"✅ Scraping complete for {name}\n")
    
    def generate_and_upload_report(self, brand, iso_week):
        """Generate report from DB and upload to sheets"""
        
        domain = brand['domain']
        name = brand['name']
        
        # Generate report
        report_data = generate_weekly_report(self.db, domain, iso_week)
        
        if not report_data:
            return False
        
        # Upload to sheets
        if self.sheets_uploader:
            print(f"    🚀 Uploading {name} {iso_week} to Google Sheets...")
            try:
                self.sheets_uploader.upload_report(name, report_data)
            except Exception as e:
                print(f"    ❌ Upload failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print(f"    ⚠️  Skipping upload (no sheets uploader configured)")
        
        del report_data
        
        return True
    
    def process_brand_reports(self, brand, weeks_back=4):
        """Generate and upload reports for recent weeks"""
        
        domain = brand['domain']
        name = brand['name']
        
        print(f"\n{'='*70}")
        print(f"GENERATING REPORTS: {name}")
        print(f"{'='*70}\n")
        
        metadata = self.get_brand_metadata(domain)
        
        if not metadata or not metadata['latest_date']:
            print(f"⚠️  No reviews found for {name}")
            return
        
        weeks = self.calculate_weeks_from_latest(metadata['latest_date'], weeks_back)
        
        if not weeks:
            print(f"⚠️  No weeks to report for {name}")
            return
        
        print(f"📅 Found {len(weeks)} weeks to report: {weeks[0]} to {weeks[-1]}")
        print(f"📊 Brand has {metadata['review_count']} total reviews\n")
        
        total_uploaded = 0
        failed = 0
        
        for iso_week in weeks:  
            if self.generate_and_upload_report(brand, iso_week):
                total_uploaded += 1
            else:
                failed += 1
        
        print(f"📊 Summary for {name}:")
        print(f"  ✅ Uploaded: {total_uploaded}")
        if failed > 0:
            print(f"  ❌ Failed: {failed}")
    
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
                if scrape:
                    self.scrape_brand(brand)
                
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
        print("Usage:")
        print("  python pipeline.py                    # Run full pipeline")
        print("  python pipeline.py --scrape-only      # Only scrape reviews")
        print("  python pipeline.py --report-only      # Only generate reports")
        print("  python pipeline.py --weeks 8          # Report last 8 weeks")
        sys.exit(0)
    
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