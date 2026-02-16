#!/usr/bin/env python3
"""
Test Script - Check W07 Reviews in Database
"""

import sys
sys.path.insert(0, '/mnt/user-data/uploads')

from db.database import Database
from datetime import datetime, timedelta

def check_week_reviews(iso_week="2026-W07"):
    """Check all reviews for a specific week"""
    
    # Parse ISO week
    year, week = map(int, iso_week.split('-W'))
    jan4 = datetime(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7) - timedelta(seconds=1)
    
    print(f"\n{'='*70}")
    print(f"CHECKING DATABASE REVIEWS FOR {iso_week}")
    print(f"{'='*70}\n")
    print(f"Week Range: {week_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"         to {week_end.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    db = Database()
    db.connect()
    
    # Get all companies
    companies = db.query("SELECT id, name, display_name FROM companies ORDER BY name")
    
    total_reviews = 0
    
    for company in companies:
        company_id = company['id']
        brand_name = company['display_name'] or company['name']
        
        # Get reviews for this week
        reviews = db.query("""
            SELECT 
                review_id,
                review_date,
                rating,
                title,
                language,
                author_name,
                verified
            FROM reviews
            WHERE company_id = %s
              AND review_date >= %s
              AND review_date < %s
            ORDER BY review_date DESC
        """, (company_id, week_start, week_end))
        
        print(f"{'─'*70}")
        print(f"BRAND: {brand_name} ({company['name']})")
        print(f"{'─'*70}")
        
        if not reviews:
            print(f"  ❌ No reviews found\n")
            continue
        
        print(f"  ✅ Found {len(reviews)} reviews:\n")
        
        for r in reviews:
            verified = "✓" if r['verified'] else "○"
            date_str = r['review_date'].strftime('%Y-%m-%d %H:%M')
            title = r['title'][:50] + "..." if r['title'] and len(r['title']) > 50 else r['title']
            
            print(f"    {date_str} | {r['rating']}★ | {verified} | {r['language']} | {title}")
            print(f"    ID: {r['review_id']}")
            print()
        
        total_reviews += len(reviews)
    
    db.close()
    
    print(f"{'='*70}")
    print(f"TOTAL: {total_reviews} reviews across all brands")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Check W07 by default, or pass different week as argument
    week = sys.argv[1] if len(sys.argv) > 1 else "2026-W07"
    check_week_reviews(week)