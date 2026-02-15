#!/usr/bin/env python3
"""
Auto Setup - Creates database, applies schema, imports topics
"""

from db.database import Database


def setup_database():
    """Create database and apply schema"""
    
    print("\n" + "="*70)
    print("AUTO DATABASE SETUP")
    print("="*70 + "\n")
    
    # Step 1: Database creation (auto-handled by db.py)
    print("📦 Connecting to database...")
    db = Database()
    db.connect()  # This auto-creates DB if missing
    
    # Step 2: Check if tables exist
    existing = db.query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public';
    """)
    
    table_names = [t['table_name'] for t in existing]
    
    if table_names:
        print(f"\n⚠️  Database already has {len(table_names)} tables:")
        for t in table_names:
            print(f"  • {t}")
        
        response = input("\nDrop and recreate? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Aborted")
            db.close()
            return
        
        # Drop all tables
        print("\n🗑️  Dropping tables...")
        db.query("DROP TABLE IF EXISTS ai_summaries CASCADE;")
        db.query("DROP TABLE IF EXISTS reviews CASCADE;")
        db.query("DROP TABLE IF EXISTS topics CASCADE;")
        db.query("DROP TABLE IF EXISTS companies CASCADE;")
        db.query("DROP TABLE IF EXISTS weekly_snapshots CASCADE;")  # Just in case
        print("  ✅ Dropped")
    
    # Step 3: Create schema
    print("\n📋 Creating tables...")
    
    db.query("""
        CREATE TABLE companies (
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
    print("  ✅ companies")
    
    db.query("""
        CREATE TABLE ai_summaries (
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
    print("  ✅ ai_summaries")
    
    db.query("""
        CREATE TABLE reviews (
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
    print("  ✅ reviews")
    
    db.query("""
        CREATE TABLE topics (
            id SERIAL PRIMARY KEY,
            topic_key VARCHAR(100) UNIQUE NOT NULL,
            topic_name VARCHAR(255) NOT NULL,
            search_terms TEXT[] NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("  ✅ topics")
    
    # Step 4: Create indexes
    print("\n🔗 Creating indexes...")
    db.query("CREATE INDEX idx_reviews_company ON reviews(company_id);")
    db.query("CREATE INDEX idx_reviews_date ON reviews(review_date);")
    db.query("CREATE INDEX idx_reviews_scraped ON reviews(scraped_at);")
    db.query("CREATE INDEX idx_ai_summaries_company ON ai_summaries(company_id);")
    db.query("CREATE INDEX idx_topics_key ON topics(topic_key);")
    print("  ✅ 5 indexes created")
    
    db.close()
    
    # Step 5: Import topics
    print("\n📥 Importing topics...")
    from db.import_topics import import_topics
    import_topics()
    
    # Step 6: Verify
    print("\n🔍 Verifying setup...")
    db.connect()
    
    tables = db.query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    
    topic_count = db.query("SELECT COUNT(*) as count FROM topics;")[0]['count']
    
    print(f"\n  Tables: {len(tables)}")
    for t in tables:
        print(f"    ✅ {t['table_name']}")
    
    print(f"\n  Topics: {topic_count}")
    
    db.close()
    
    print("\n" + "="*70)
    print("✅ SETUP COMPLETE")
    print("="*70)
    print("  python preflight_check.py")
    print()


if __name__ == "__main__":
    setup_database()