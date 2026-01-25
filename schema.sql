-- Drop tables if they exist (for clean recreation)
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS top_mentions CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- Companies table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    business_id VARCHAR(255) UNIQUE NOT NULL,
    brand_name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    logo_url VARCHAR(500),
    total_reviews INTEGER DEFAULT 0,
    trust_score DECIMAL(3,2),
    stars DECIMAL(3,2),
    is_claimed BOOLEAN DEFAULT FALSE,
    categories TEXT[],
    ai_summary_text TEXT,
    ai_summary_updated_at TIMESTAMP,
    ai_summary_language VARCHAR(10),
    ai_summary_model_version VARCHAR(50),
    last_scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Reviews table
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    review_id VARCHAR(255) UNIQUE NOT NULL,
    consumer_name VARCHAR(255),
    consumer_id VARCHAR(255),
    consumer_reviews_count INTEGER,
    consumer_country_code VARCHAR(10),
    title TEXT,
    text TEXT,
    rating INTEGER,
    published_date TIMESTAMP,
    updated_date TIMESTAMP,
    experience_date DATE,
    verified BOOLEAN DEFAULT FALSE,
    reply_message TEXT,
    reply_published_date TIMESTAMP,
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Top mentions table
CREATE TABLE top_mentions (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    mention VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, mention)
);

-- Create indexes for better query performance
CREATE INDEX idx_reviews_company_id ON reviews(company_id);
CREATE INDEX idx_reviews_published_date ON reviews(published_date);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_companies_business_id ON companies(business_id);
CREATE INDEX idx_top_mentions_company_id ON top_mentions(company_id);