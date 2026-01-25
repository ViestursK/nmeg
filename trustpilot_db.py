from db import Database
from datetime import datetime

class TrustpilotDB:
    def __init__(self):
        self.db = Database()
    
    def init_schema(self):
        """Initialize database schema from schema.sql"""
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
        
        conn = self.db.connect()
        cur = conn.cursor()
        cur.execute(schema_sql)
        conn.commit()
        cur.close()
        print("✅ Database schema initialized")
    
    def upsert_company(self, company_data):
        """Insert or update company data"""
        ai_summary = company_data.get('ai_summary') or {}
        
        sql = """
        INSERT INTO companies (
            business_id, brand_name, website, logo_url, 
            total_reviews, trust_score, stars, is_claimed, 
            categories, ai_summary_text, ai_summary_updated_at, 
            ai_summary_language, ai_summary_model_version,
            last_scraped_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON CONFLICT (business_id) 
        DO UPDATE SET
            brand_name = EXCLUDED.brand_name,
            website = EXCLUDED.website,
            logo_url = EXCLUDED.logo_url,
            total_reviews = EXCLUDED.total_reviews,
            trust_score = EXCLUDED.trust_score,
            stars = EXCLUDED.stars,
            is_claimed = EXCLUDED.is_claimed,
            categories = EXCLUDED.categories,
            ai_summary_text = EXCLUDED.ai_summary_text,
            ai_summary_updated_at = EXCLUDED.ai_summary_updated_at,
            ai_summary_language = EXCLUDED.ai_summary_language,
            ai_summary_model_version = EXCLUDED.ai_summary_model_version,
            last_scraped_at = NOW(),
            updated_at = NOW()
        RETURNING id;
        """
        
        params = (
            company_data['business_id'],
            company_data['brand_name'],
            company_data.get('website'),
            company_data.get('logo_url'),
            company_data.get('total_reviews', 0),
            company_data.get('trust_score'),
            company_data.get('stars'),
            company_data.get('is_claimed', False),
            company_data.get('categories', []),
            ai_summary.get('summary') if ai_summary else None,
            self._parse_datetime(ai_summary.get('updatedAt')) if ai_summary else None,
            ai_summary.get('language') if ai_summary else None,
            ai_summary.get('modelVersion') if ai_summary else None
        )
        
        result = self.db.query(sql, params)
        company_id = result[0]['id']
        print(f"✅ Company saved: {company_data['brand_name']} (ID: {company_id})")
        return company_id
    
    def insert_top_mentions(self, company_id, mentions):
        """Insert top mentions for a company"""
        if not mentions:
            return
        
        # Delete existing mentions first
        self.db.query("DELETE FROM top_mentions WHERE company_id = %s", (company_id,))
        
        # Insert new mentions
        for mention in mentions:
            sql = """
            INSERT INTO top_mentions (company_id, mention)
            VALUES (%s, %s)
            ON CONFLICT (company_id, mention) DO NOTHING
            """
            self.db.query(sql, (company_id, mention))
        
        print(f"✅ Inserted {len(mentions)} top mentions")
    
    def insert_review(self, company_id, review_data):
        """Insert a single review"""
        dates = review_data.get('dates', {})
        consumer = review_data.get('consumer', {})
        reply = review_data.get('reply')
        
        sql = """
        INSERT INTO reviews (
            company_id, review_id, consumer_name, consumer_id,
            consumer_reviews_count, consumer_country_code,
            title, text, rating, published_date, updated_date,
            experience_date, verified, reply_message, reply_published_date,
            language
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (review_id) DO NOTHING
        """
        
        params = (
            company_id,
            review_data['id'],
            consumer.get('displayName'),
            consumer.get('id'),
            consumer.get('numberOfReviews'),
            consumer.get('countryCode'),
            review_data.get('title'),
            review_data.get('text'),
            review_data.get('rating'),
            self._parse_datetime(dates.get('publishedDate')),
            self._parse_datetime(dates.get('updatedDate')),
            self._parse_date(dates.get('experiencedDate')),
            review_data.get('isVerified', False),
            reply.get('message') if reply else None,
            self._parse_datetime(reply.get('publishedDate')) if reply else None,
            review_data.get('language', 'en')
        )
        
        self.db.query(sql, params)
    
    def insert_reviews_batch(self, company_id, reviews):
        """Insert multiple reviews"""
        count = 0
        for review in reviews:
            try:
                self.insert_review(company_id, review)
                count += 1
            except Exception as e:
                print(f"  [!] Failed to insert review {review.get('id')}: {e}")
        
        print(f"✅ Inserted {count}/{len(reviews)} reviews")
        return count
    
    def get_company_stats(self, business_id):
        """Get company statistics"""
        sql = """
        SELECT 
            c.*,
            COUNT(r.id) as stored_reviews,
            COUNT(CASE WHEN r.published_date >= NOW() - INTERVAL '7 days' THEN 1 END) as week_reviews
        FROM companies c
        LEFT JOIN reviews r ON c.id = r.company_id
        WHERE c.business_id = %s
        GROUP BY c.id
        """
        result = self.db.query(sql, (business_id,))
        return result[0] if result else None
    
    def _parse_datetime(self, dt_string):
        """Parse ISO datetime string"""
        if not dt_string:
            return None
        try:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            return None
    
    def _parse_date(self, date_string):
        """Parse ISO date string"""
        if not date_string:
            return None
        try:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00')).date()
        except:
            return None
    
    def close(self):
        """Close database connection"""
        self.db.close()