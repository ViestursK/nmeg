#!/usr/bin/env python3
"""
Compare Database vs Trustpilot for a specific week
"""

import sys
sys.path.insert(0, '/mnt/user-data/uploads')

from db.database import Database
from scraper import TrustpilotScraper
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json

def compare_week(brand_domain, iso_week="2026-W07"):
    """Compare DB vs Trustpilot for a specific week"""
    
    # Parse ISO week
    year, week = map(int, iso_week.split('-W'))
    jan4 = datetime(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7) - timedelta(seconds=1)
    
    print(f"\n{'='*70}")
    print(f"COMPARISON: {brand_domain} - {iso_week}")
    print(f"{'='*70}\n")
    print(f"Week Range: {week_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"         to {week_end.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Check Database
    print("📊 CHECKING DATABASE...\n")
    
    db = Database()
    db.connect()
    
    company = db.query("SELECT id FROM companies WHERE name = %s", (brand_domain,))
    if not company:
        print(f"❌ Brand not found in database: {brand_domain}")
        return
    
    company_id = company[0]['id']
    
    db_reviews = db.query("""
        SELECT 
            review_id,
            review_date,
            rating,
            title
        FROM reviews
        WHERE company_id = %s
          AND review_date >= %s
          AND review_date < %s
        ORDER BY review_date DESC
    """, (company_id, week_start, week_end))
    
    print(f"Database: {len(db_reviews)} reviews\n")
    
    if db_reviews:
        print("Reviews in DB:")
        for r in db_reviews:
            date_str = r['review_date'].strftime('%Y-%m-%d %H:%M')
            print(f"  {date_str} | {r['rating']}★ | {r['review_id'][:20]}...")
        print()
    
    # 2. Check Trustpilot (manually count for this week)
    print("🔍 CHECKING TRUSTPILOT...\n")
    print("Fetching reviews from Trustpilot...")
    
    scraper = TrustpilotScraper(db)
    
    # Get first few pages from Trustpilot
    base_url = f"https://www.trustpilot.com/review/{brand_domain}"
    params = {"languages": "all", "page": 1}
    
    session = requests.Session()
    session.headers.update(scraper._get_headers())
    
    trustpilot_reviews_in_week = []
    
    for page in range(1, 6):  # Check first 5 pages
        params['page'] = page
        try:
            response = session.get(base_url, params=params, timeout=30)
            if response.status_code != 200:
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            next_data = soup.find('script', {'id': '__NEXT_DATA__'})
            if not next_data:
                break
            
            data = json.loads(next_data.string)
            reviews = data.get('props', {}).get('pageProps', {}).get('reviews', [])
            
            if not reviews:
                break
            
            for review in reviews:
                dates = review.get('dates', {})
                review_date_str = dates.get('publishedDate')
                if not review_date_str:
                    continue
                
                review_date = datetime.fromisoformat(review_date_str.replace('Z', '+00:00'))
                review_date = review_date.replace(tzinfo=None)  # Remove timezone
                
                if week_start <= review_date < week_end:
                    trustpilot_reviews_in_week.append({
                        'id': review.get('id'),
                        'date': review_date,
                        'rating': review.get('rating'),
                        'title': review.get('title')
                    })
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    print(f"Trustpilot: {len(trustpilot_reviews_in_week)} reviews in {iso_week}\n")
    
    if trustpilot_reviews_in_week:
        print("Reviews on Trustpilot:")
        for r in trustpilot_reviews_in_week:
            date_str = r['date'].strftime('%Y-%m-%d %H:%M')
            print(f"  {date_str} | {r['rating']}★ | {r['id'][:20]}...")
        print()
    
    # 3. Compare
    print(f"{'='*70}")
    print("COMPARISON RESULTS")
    print(f"{'='*70}\n")
    
    db_count = len(db_reviews)
    tp_count = len(trustpilot_reviews_in_week)
    
    print(f"Database:   {db_count} reviews")
    print(f"Trustpilot: {tp_count} reviews")
    
    if db_count == tp_count:
        print("\n✅ MATCH - Counts are equal")
    else:
        print(f"\n❌ MISMATCH - Difference: {abs(db_count - tp_count)} reviews")
        
        # Find missing
        db_ids = {r['review_id'] for r in db_reviews}
        tp_ids = {r['id'] for r in trustpilot_reviews_in_week}
        
        missing_in_db = tp_ids - db_ids
        extra_in_db = db_ids - tp_ids
        
        if missing_in_db:
            print(f"\n⚠️  Missing in DB ({len(missing_in_db)}):")
            for review_id in missing_in_db:
                r = next((x for x in trustpilot_reviews_in_week if x['id'] == review_id), None)
                if r:
                    print(f"  {r['date'].strftime('%Y-%m-%d %H:%M')} | {r['rating']}★ | {review_id[:30]}...")
        
        if extra_in_db:
            print(f"\n⚠️  Extra in DB ({len(extra_in_db)}):")
            for review_id in extra_in_db:
                r = next((x for x in db_reviews if x['review_id'] == review_id), None)
                if r:
                    print(f"  {r['review_date'].strftime('%Y-%m-%d %H:%M')} | {r['rating']}★ | {review_id[:30]}...")
    
    print()
    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_comparison.py <brand_domain> [iso_week]")
        print("Example: python test_comparison.py certifiedfasting.com 2026-W07")
        sys.exit(1)
    
    brand = sys.argv[1]
    week = sys.argv[2] if len(sys.argv) > 2 else "2026-W07"
    
    compare_week(brand, week)