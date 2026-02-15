from db.database import Database

def reset_database():
    """Drop all existing tables and recreate with new schema"""
    db = Database()
    
    print("⚠️  WARNING: This will delete ALL existing data!")
    response = input("Type 'yes' to continue: ")
    
    if response.lower() != 'yes':
        print("❌ Aborted")
        return
    
    print("\n🗑️  Dropping old tables...")
    
    # Drop tables in reverse order of dependencies
    db.query("DROP TABLE IF EXISTS ai_summaries CASCADE;")
    print("  Dropped ai_summaries")
    
    db.query("DROP TABLE IF EXISTS reviews CASCADE;")
    print("  Dropped reviews")
    
    db.query("DROP TABLE IF EXISTS topics CASCADE;")
    print("  Dropped topics")
    
    db.query("DROP TABLE IF EXISTS companies CASCADE;")
    print("  Dropped companies")
    
    print("\n✅ All old tables dropped")
    print("\n📦 Creating new schema...")
    
    # Companies table - stores all business unit metadata
    db.query("""
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            business_id VARCHAR(255),
            display_name VARCHAR(255),
            website_url TEXT,
            logo_url TEXT,
            star_rating_svg VARCHAR(500),
            total_reviews INTEGER,
            trust_score NUMERIC(3,2),
            stars INTEGER,
            is_claimed BOOLEAN,
            categories JSONB,
            verification JSONB,
            contact_info JSONB,
            activity JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created 'companies' table")
    
    # AI summaries table
    db.query("""
        CREATE TABLE IF NOT EXISTS ai_summaries (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            summary_text TEXT,
            summary_language VARCHAR(10),
            model_version VARCHAR(50),
            topics JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_id)
        );
    """)
    print("✅ Created 'ai_summaries' table")
    
    # Reviews table
    db.query("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            review_id VARCHAR(255) UNIQUE NOT NULL,
            rating INTEGER,
            title TEXT,
            text TEXT,
            text_en TEXT,
            author_name VARCHAR(255),
            author_id VARCHAR(255),
            author_country_code VARCHAR(10),
            author_review_count INTEGER,
            review_date TIMESTAMP,
            experience_date DATE,
            verified BOOLEAN DEFAULT FALSE,
            language VARCHAR(10),
            reply_message TEXT,
            reply_date TIMESTAMP,
            likes INTEGER DEFAULT 0,
            source VARCHAR(50),
            labels JSONB,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_edited BOOLEAN DEFAULT FALSE
        );
    """)
    print("✅ Created 'reviews' table")
    
    # Topics table
    db.query("""
        CREATE TABLE IF NOT EXISTS topics (
            id SERIAL PRIMARY KEY,
            topic_key VARCHAR(100) UNIQUE NOT NULL,
            topic_name VARCHAR(255) NOT NULL,
            search_terms TEXT[] NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ Created 'topics' table")
    
    # Create indexes
    db.query("CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews(company_id);")
    db.query("CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(review_date);")
    db.query("CREATE INDEX IF NOT EXISTS idx_reviews_scraped ON reviews(scraped_at);")
    db.query("CREATE INDEX IF NOT EXISTS idx_ai_summaries_company ON ai_summaries(company_id);")
    db.query("CREATE INDEX IF NOT EXISTS idx_topics_key ON topics(topic_key);")
    print("✅ Created indexes")
    
    db.close()
    print("\n🎉 Database reset complete! Ready to scrape.")

if __name__ == "__main__":
    reset_database()