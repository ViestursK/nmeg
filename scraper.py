#!/usr/bin/env python3
"""
Trustpilot Scraper - PostgreSQL Version
Saves all data directly to PostgreSQL database
"""

import json
import requests
import re
from datetime import datetime, timedelta
import time
from trustpilot_db import TrustpilotDB

# =============================================================================
# CONFIGURATION (Edit these)
# =============================================================================

BRAND_DOMAIN = "simple-life-app.com"  # Change this to scrape different brand
MAX_PAGES = 10  # Number of pages to scrape

# =============================================================================
# CONSTANTS
# =============================================================================

QUERY_PARAMS = "languages=all"  # No date filter = full scrape
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Load topic translation map
with open('tp_topics.json', encoding='utf-8') as f:
    ALL_TOPICS = json.load(f)
    print(f"[+] Loaded {len(ALL_TOPICS)} Trustpilot topics")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_next_data(html):
    """Extract __NEXT_DATA__ JSON from HTML"""
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if match:
        return json.loads(match.group(1))
    return None

def get_top_mentions(business_id):
    """Fetch and translate top mentions/topics for the business"""
    url = f'https://www.trustpilot.com/api/businessunitprofile/businessunit/{business_id}/service-reviews/topics'
    try:
        response = requests.get(url, headers=HEADERS)
        response_data = json.loads(response.text)
        
        options = response_data['topics']
        
        translated_topics = []
        for topic in options:
            readable_name = ALL_TOPICS.get(topic, topic.replace('_', ' ').title())
            translated_topics.append(readable_name)
        
        return translated_topics
    except Exception as e:
        print(f"  [!] Failed to fetch top mentions: {e}")
        return []

# =============================================================================
# MAIN SCRAPER
# =============================================================================

def scrape_brand(brand_domain, max_pages=10, db=None):
    """
    Scrape a single brand and save to database
    """
    print(f"\n{'='*70}")
    print(f"SCRAPING: {brand_domain}")
    print(f"{'='*70}\n")
    
    BASE_URL_CLEAN = f"https://www.trustpilot.com/review/{brand_domain}"
    BASE_URL = f"{BASE_URL_CLEAN}?{QUERY_PARAMS}"
    
    all_reviews = []
    company_data = {}
    business_id = None
    
    # Step 1: Fetch AI Summary from clean URL
    print(f"[1] Fetching AI summary and company info...")
    response_clean = requests.get(BASE_URL_CLEAN, headers=HEADERS)
    
    if response_clean.status_code != 200:
        print(f"[!] Failed to fetch page: HTTP {response_clean.status_code}")
        return None
    
    data_clean = extract_next_data(response_clean.text)
    if not data_clean:
        print("[!] Could not extract data from page")
        return None
    
    # Step 2: Fetch filtered reviews
    print(f"[2] Fetching filtered reviews...")
    response = requests.get(BASE_URL, headers=HEADERS)
    
    if response.status_code != 200:
        data = data_clean
    else:
        data = extract_next_data(response.text)
        if not data:
            data = data_clean
    
    try:
        # Get AI summary from clean URL data
        page_props_clean = data_clean["props"]["pageProps"]
        business_unit = page_props_clean["businessUnit"]
        
        # Get reviews from filtered URL data
        page_props = data["props"]["pageProps"]
        
        # Extract company information
        company_data = {
            "brand_name": business_unit["displayName"],
            "business_id": business_unit["id"],
            "website": business_unit.get("websiteUrl", "N/A"),
            "logo_url": business_unit.get("profileImageUrl", ""),
            "total_reviews": business_unit["numberOfReviews"],
            "trust_score": business_unit["trustScore"],
            "stars": business_unit.get("stars", business_unit["trustScore"]),
            "is_claimed": business_unit.get("isClaimed", False),
            "categories": [cat["name"] for cat in business_unit.get("categories", [])],
        }
        
        # Fix logo URL
        if company_data["logo_url"] and company_data["logo_url"].startswith("//"):
            company_data["logo_url"] = "https:" + company_data["logo_url"]
        
        business_id = company_data["business_id"]
        
        # Get AI Summary
        ai_summary_data = page_props_clean.get("aiSummary")
        if ai_summary_data:
            company_data["ai_summary"] = {
                "summary": ai_summary_data.get("summary", "N/A"),
                "updatedAt": ai_summary_data.get("updatedAt", "N/A"),
                "language": ai_summary_data.get("lang", "en"),
                "modelVersion": ai_summary_data.get("modelVersion", "N/A")
            }
            print("  [+] AI Summary extracted")
        else:
            company_data["ai_summary"] = None
            print("  [!] No AI Summary available")
        
        # Get initial reviews
        initial_reviews = page_props.get("reviews", [])
        all_reviews.extend(initial_reviews)
        print(f"  [+] Extracted {len(initial_reviews)} reviews from page 1")
        
        # Get Top Mentions
        if business_id:
            company_data["top_mentions"] = get_top_mentions(business_id)
        
        print(f"\n[+] Company Data Extracted:")
        print(f"    Brand: {company_data['brand_name']}")
        print(f"    Total Reviews: {company_data['total_reviews']}")
        print(f"    Trust Score: {company_data['trust_score']}/5")
        
    except KeyError as e:
        print(f"[!] Failed to extract company data: {e}")
        return None
    
    # Pagination
    if max_pages and max_pages > 1:
        print(f"\n[3] Fetching additional pages (up to {max_pages-1} more)...")
        page = 2
        
        while page <= max_pages:
            print(f"\n  Fetching page {page}...")
            url = f"{BASE_URL}&page={page}"
            
            response = requests.get(url, headers=HEADERS)
            
            if response.status_code == 404:
                print(f"  [X] Reached end of pages")
                break
            
            data = extract_next_data(response.text)
            if not data:
                break
            
            try:
                reviews = data["props"]["pageProps"]["reviews"]
                if not reviews:
                    break
                
                all_reviews.extend(reviews)
                print(f"  [+] Extracted {len(reviews)} reviews (Total: {len(all_reviews)})")
                
            except KeyError:
                break
            
            page += 1
            time.sleep(2)
    
    
    print(f"\n{'='*70}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"Total Reviews Extracted: {len(all_reviews)}")
    
    # Save to database if db connection provided
    if db:
        print(f"\n[4] Saving to database...")
        
        # Save company
        company_id = db.upsert_company(company_data)
        
        # Save top mentions
        if company_data.get('top_mentions'):
            db.insert_top_mentions(company_id, company_data['top_mentions'])
        
        # Save reviews
        db.insert_reviews_batch(company_id, all_reviews)
        
        # Get final stats
        stats = db.get_company_stats(business_id)
        print(f"\n[✓] Database Summary:")
        print(f"    Brand: {stats['brand_name']}")
        print(f"    Stored Reviews: {stats['stored_reviews']}")
        print(f"    Past Week: {stats['week_reviews']}")
        
        return company_id
    
    return company_data

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("\n" + "="*70)
    print("TRUSTPILOT SCRAPER - PostgreSQL Version")
    print("="*70 + "\n")
    
    # Initialize database
    db = TrustpilotDB()
    
    # Initialize schema (comment out after first run)
    print("[*] Initializing database schema...")
    db.init_schema()
    
    try:
        # Scrape the brand
        company_id = scrape_brand(BRAND_DOMAIN, max_pages=MAX_PAGES, db=db)
        
        if company_id:
            print(f"\n[✓] Successfully scraped and saved to database!")
            print(f"    Company ID: {company_id}")
        else:
            print("\n[!] Scraping failed")
    
    finally:
        # Close database connection
        db.close()

if __name__ == "__main__":
    main()