import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

class TrustpilotScraper:
    def __init__(self, db):
        self.db = db
        self.jwt_token = os.getenv("TRUSTPILOT_JWT")
        
        if not self.jwt_token or self.jwt_token == "your.jwt.token":
            print("⚠️  No JWT token configured - limited to ~10 pages")
        else:
            print("🔑 Authenticated")
        
    def _get_headers(self):
        """Build request headers with JWT cookie"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        
        if self.jwt_token:
            headers["Cookie"] = f"jwt={self.jwt_token};"
            
        return headers
    
    def _brand_exists(self, company_name):
        """Check if brand already exists in database"""
        result = self.db.query(
            "SELECT id FROM companies WHERE name = %s LIMIT 1;",
            (company_name,)
        )
        return bool(result)
    
    def _save_company_metadata(self, company_id, page_props):
        """Save/update company metadata from businessUnit"""
        business_unit = page_props.get('businessUnit', {})
        
        if not business_unit:
            return
        
        # Build star rating SVG URL based on stars
        stars = business_unit.get('stars', 0)
        star_rating_svg = f"https://cdn.trustpilot.net/brand-assets/4.1.0/stars/stars-{stars}.svg" if stars else None
        
        self.db.query("""
            UPDATE companies SET
                business_id = %s,
                display_name = %s,
                website_url = %s,
                logo_url = %s,
                total_reviews = %s,
                trust_score = %s,
                stars = %s,
                star_rating_svg = %s,
                is_claimed = %s,
                categories = %s,
                verification = %s,
                contact_info = %s,
                activity = %s,
                updated_at = NOW()
            WHERE id = %s;
        """, (
            business_unit.get('id'),
            business_unit.get('displayName'),
            business_unit.get('websiteUrl'),
            business_unit.get('profileImageUrl'),
            business_unit.get('numberOfReviews'),
            business_unit.get('trustScore'),
            business_unit.get('stars'),
            star_rating_svg,
            business_unit.get('isClaimed'),
            json.dumps(business_unit.get('categories', [])),
            json.dumps(business_unit.get('verification', {})),
            json.dumps(business_unit.get('contactInfo', {})),
            json.dumps(business_unit.get('activity', {})),
            company_id
        ))
    
    def _save_ai_summary(self, company_id, page_props):
        """Save/update AI summary from correct location in page_props"""
        # AI summary is at same level as businessUnit and reviews
        ai_summary = page_props.get('aiSummary', {})
        
        if not ai_summary:
            print("  ℹ️  No AI summary available for this company")
            return
        
        # Check if summary exists
        existing = self.db.query(
            "SELECT id FROM ai_summaries WHERE company_id = %s;",
            (company_id,)
        )
        
        if existing:
            self.db.query("""
                UPDATE ai_summaries SET
                    summary_text = %s,
                    summary_language = %s,
                    model_version = %s,
                    created_at = NOW()
                WHERE company_id = %s;
            """, (
                ai_summary.get('summary'),
                ai_summary.get('lang'),
                ai_summary.get('modelVersion'),
                company_id
            ))
        else:
            self.db.query("""
                INSERT INTO ai_summaries (
                    company_id, summary_text, summary_language, model_version
                ) VALUES (%s, %s, %s, %s);
            """, (
                company_id,
                ai_summary.get('summary'),
                ai_summary.get('lang'),
                ai_summary.get('modelVersion')
            ))
        
        print(f"  ✓ AI summary saved ({ai_summary.get('lang', 'unknown')} - {ai_summary.get('modelVersion', 'unknown')})")
    
    def _fetch_and_save_topics(self, company_id, business_id):
        """Fetch top mentions/topics from separate API"""
        if not business_id:
            return
        
        url = f'https://www.trustpilot.com/api/businessunitprofile/businessunit/{business_id}/service-reviews/topics'
        
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            
            topics = data.get('topics', [])
            
            if not topics:
                return
            
            print(f"  🏷️  Found {len(topics)} topics")
            
            # Update ai_summaries with topics
            existing = self.db.query(
                "SELECT id FROM ai_summaries WHERE company_id = %s;",
                (company_id,)
            )
            
            if existing:
                self.db.query("""
                    UPDATE ai_summaries SET topics = %s WHERE company_id = %s;
                """, (json.dumps(topics), company_id))
            else:
                # Create record with just topics
                self.db.query("""
                    INSERT INTO ai_summaries (company_id, topics) VALUES (%s, %s);
                """, (company_id, json.dumps(topics)))
                
        except Exception as e:
            print(f"  ⚠️  Failed to fetch topics: {e}")
    
    def _should_save_review(self, company_id, review):
        """Check if review already exists (without saving)"""
        review_id = review.get("id")
        existing = self.db.query(
            "SELECT 1 FROM reviews WHERE review_id = %s LIMIT 1;",
            (review_id,)
        )
        return not existing
    
    def _save_review_batch(self, batch):
        """Save multiple reviews in single transaction"""
        if not batch:
            return
        
        conn = self.db.connect()
        cur = conn.cursor()
        
        for company_id, review in batch:
            consumer = review.get("consumer", {})
            dates = review.get("dates", {})
            labels = review.get("labels", {})
            verification = labels.get("verification", {})
            reply = review.get("reply")
            
            cur.execute("""
                INSERT INTO reviews (
                    company_id, review_id, rating, title, text,
                    author_name, author_id, author_country_code, author_review_count,
                    review_date, experience_date, verified, language,
                    reply_message, reply_date, likes, source, labels, is_edited
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (review_id) DO NOTHING;
            """, (
                company_id,
                review.get("id"),
                review.get("rating"),
                review.get("title"),
                review.get("text"),
                consumer.get("displayName"),
                consumer.get("id"),
                consumer.get("countryCode"),
                consumer.get("numberOfReviews"),
                dates.get("publishedDate"),
                dates.get("experiencedDate"),
                verification.get("isVerified", False),
                review.get("language"),
                reply.get("message") if reply else None,
                reply.get("publishedDate") if reply else None,
                review.get("likes", 0),
                review.get("source"),
                json.dumps(labels),
                dates.get("updatedDate") is not None
            ))
        
        conn.commit()
        cur.close()
    
    def scrape_and_save(self, company_domain, use_date_filter=None, batch_size=100):
        """
        Scrape reviews and save in batches for performance
        
        Args:
            company_domain: e.g., "ketogo.app"
            use_date_filter: If None, auto-detect based on brand existence
            batch_size: Commit to DB every N reviews (default 100)
        """
        # Auto-detect if not specified
        if use_date_filter is None:
            use_date_filter = self._brand_exists(company_domain)
        
        # Get or create company
        company = self.db.query(
            "SELECT id FROM companies WHERE name = %s;",
            (company_domain,)
        )
        
        if not company:
            self.db.query(
                "INSERT INTO companies (name) VALUES (%s) RETURNING id;",
                (company_domain,)
            )
            company = self.db.query("SELECT id FROM companies WHERE name = %s;", (company_domain,))
        
        company_id = company[0]["id"]
        
        # Build base URL
        base_url = f"https://www.trustpilot.com/review/{company_domain}"
        
        # Build params
        params = {}
        
        if use_date_filter:
            params["date"] = "last30days"
            print(f"🔄 Incremental mode: Fetching last 30 days for {company_domain}")
        else:
            print(f"📥 Backfill mode: Fetching full history for {company_domain}")
        
        params["languages"] = "all"
        
        all_reviews = []
        total_inserted = 0
        page = 1
        total_reviews = None
        estimated_pages = None
        
        # Batch tracking
        batch_buffer = []
        consecutive_empty_pages = 0
        
        session = requests.Session()
        session.headers.update(self._get_headers())
        
        while True:
            params["page"] = page
            
            try:
                response = session.get(base_url, params=params, timeout=30)
                
                if response.status_code == 404:
                    print(f"\n⚠️  Reached end at page {page}")
                    break
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                next_data = soup.find('script', {'id': '__NEXT_DATA__'})
                
                if not next_data:
                    print(f"\n⚠️  Page {page}: No data found")
                    break
                
                data = json.loads(next_data.string)
                page_props = data.get('props', {}).get('pageProps', {})
                reviews = page_props.get('reviews', [])
                
                # Extract and save metadata from first page
                if page == 1:
                    self._save_company_metadata(company_id, page_props)
                    self._save_ai_summary(company_id, page_props)
                    
                    business_unit = page_props.get('businessUnit', {})
                    business_id = business_unit.get('id')
                    if business_id:
                        self._fetch_and_save_topics(company_id, business_id)
                    
                    if not total_reviews:
                        business_unit = page_props.get('businessUnit', {})
                        num_reviews = business_unit.get('numberOfReviews')
                        
                        if isinstance(num_reviews, int):
                            total_reviews = num_reviews
                        elif isinstance(num_reviews, dict):
                            total_reviews = num_reviews.get('total')
                        
                        if total_reviews:
                            if use_date_filter:
                                print(f"📊 Total reviews: {total_reviews:,} (filtering last 30 days)")
                            else:
                                estimated_pages = (total_reviews + 19) // 20
                                print(f"📊 Total reviews: {total_reviews:,} (~{estimated_pages} pages)")
                
                if not reviews:
                    print(f"\n✓ Completed at page {page}")
                    break
                
                # Add to batch buffer
                new_saves_this_page = 0
                for review in reviews:
                    if self._should_save_review(company_id, review):
                        batch_buffer.append((company_id, review))
                        new_saves_this_page += 1
                
                # Commit batch if full
                if len(batch_buffer) >= batch_size:
                    self._save_review_batch(batch_buffer)
                    total_inserted += len(batch_buffer)
                    batch_buffer = []
                
                all_reviews.extend(reviews)
                
                # Early stopping for incremental mode
                if use_date_filter:
                    if new_saves_this_page == 0:
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 2:
                            print(f"\n✓ Early stop: 2 consecutive pages with no new reviews")
                            break
                    else:
                        consecutive_empty_pages = 0
                
                # Show progress
                if estimated_pages:
                    progress = (page / estimated_pages) * 100
                    print(f"  Page {page}/{estimated_pages}: {len(reviews)} reviews | New: {new_saves_this_page} | Buffered: {len(batch_buffer)} ({progress:.0f}%)")
                else:
                    print(f"  Page {page}: {len(reviews)} reviews | New: {new_saves_this_page} | Buffered: {len(batch_buffer)}")
                
            except Exception as e:
                print(f"\n❌ Error on page {page}: {e}")
                break
            
            page += 1
        
        # Save remaining batch
        if batch_buffer:
            self._save_review_batch(batch_buffer)
            total_inserted += len(batch_buffer)
        
        # Update company timestamp
        self.db.query(
            "UPDATE companies SET updated_at = NOW() WHERE id = %s;",
            (company_id,)
        )
        
        print(f"\n✅ Fetched: {len(all_reviews):,} reviews")
        print(f"✅ Saved: {total_inserted:,} new reviews")
        
        return all_reviews