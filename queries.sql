-- ============================================================================
-- BASIC DATA CHECKS
-- ============================================================================

-- 1. Count records in each table
SELECT 'companies' as table_name, COUNT(*) as count FROM companies
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'top_mentions', COUNT(*) FROM top_mentions;

-- 2. List all companies
SELECT 
    id,
    brand_name,
    business_id,
    total_reviews,
    trust_score,
    stars,
    last_scraped_at
FROM companies
ORDER BY last_scraped_at DESC;

-- 3. Get company with full details
SELECT 
    c.*,
    COUNT(r.id) as stored_reviews,
    COUNT(CASE WHEN r.published_date >= NOW() - INTERVAL '7 days' THEN 1 END) as past_week_reviews
FROM companies c
LEFT JOIN reviews r ON c.id = r.company_id
WHERE c.brand_name = 'Simple Life'  -- Change brand name here
GROUP BY c.id;

-- ============================================================================
-- REVIEW QUERIES
-- ============================================================================

-- 4. Latest 10 reviews for a company
SELECT 
    c.brand_name,
    r.title,
    r.rating,
    r.text,
    r.consumer_name,
    r.published_date,
    r.verified
FROM reviews r
JOIN companies c ON r.company_id = c.id
WHERE c.brand_name = 'Simple Life'  -- Change brand name here
ORDER BY r.published_date DESC
LIMIT 10;

-- 5. Reviews from past 7 days
SELECT 
    c.brand_name,
    r.title,
    r.rating,
    r.published_date
FROM reviews r
JOIN companies c ON r.company_id = c.id
WHERE r.published_date >= NOW() - INTERVAL '7 days'
ORDER BY r.published_date DESC;

-- 6. Reviews by rating distribution
SELECT 
    c.brand_name,
    r.rating,
    COUNT(*) as count
FROM reviews r
JOIN companies c ON r.company_id = c.id
GROUP BY c.brand_name, r.rating
ORDER BY c.brand_name, r.rating DESC;

-- 7. Average rating per company
SELECT 
    c.brand_name,
    c.trust_score as trustpilot_score,
    ROUND(AVG(r.rating)::numeric, 2) as avg_rating_from_reviews,
    COUNT(r.id) as review_count
FROM companies c
LEFT JOIN reviews r ON c.id = r.company_id
GROUP BY c.id
ORDER BY avg_rating_from_reviews DESC;

-- ============================================================================
-- TOP MENTIONS
-- ============================================================================

-- 8. Get top mentions for a company
SELECT 
    c.brand_name,
    m.mention
FROM top_mentions m
JOIN companies c ON m.company_id = c.id
WHERE c.brand_name = 'Simple Life'  -- Change brand name here
ORDER BY m.mention;

-- 9. All top mentions with company names
SELECT 
    c.brand_name,
    STRING_AGG(m.mention, ', ') as mentions
FROM companies c
LEFT JOIN top_mentions m ON c.id = m.company_id
GROUP BY c.id, c.brand_name
ORDER BY c.brand_name;

-- ============================================================================
-- TIME-BASED ANALYSIS
-- ============================================================================

-- 10. Reviews per month (last 12 months)
SELECT 
    c.brand_name,
    DATE_TRUNC('month', r.published_date) as month,
    COUNT(*) as review_count,
    ROUND(AVG(r.rating)::numeric, 2) as avg_rating
FROM reviews r
JOIN companies c ON r.company_id = c.id
WHERE r.published_date >= NOW() - INTERVAL '12 months'
GROUP BY c.brand_name, DATE_TRUNC('month', r.published_date)
ORDER BY c.brand_name, month DESC;

-- 11. Reviews per day (last 30 days)
SELECT 
    c.brand_name,
    DATE(r.published_date) as date,
    COUNT(*) as review_count
FROM reviews r
JOIN companies c ON r.company_id = c.id
WHERE r.published_date >= NOW() - INTERVAL '30 days'
GROUP BY c.brand_name, DATE(r.published_date)
ORDER BY date DESC;

-- ============================================================================
-- VERIFICATION & QUALITY CHECKS
-- ============================================================================

-- 12. Verified vs unverified reviews
SELECT 
    c.brand_name,
    r.verified,
    COUNT(*) as count,
    ROUND(AVG(r.rating)::numeric, 2) as avg_rating
FROM reviews r
JOIN companies c ON r.company_id = c.id
GROUP BY c.brand_name, r.verified
ORDER BY c.brand_name, r.verified DESC;

-- 13. Reviews with company replies
SELECT 
    c.brand_name,
    COUNT(*) as total_reviews,
    COUNT(CASE WHEN r.reply_message IS NOT NULL THEN 1 END) as reviews_with_reply,
    ROUND(
        COUNT(CASE WHEN r.reply_message IS NOT NULL THEN 1 END)::numeric / 
        COUNT(*)::numeric * 100, 2
    ) as reply_rate_percent
FROM reviews r
JOIN companies c ON r.company_id = c.id
GROUP BY c.brand_name;

-- ============================================================================
-- AI SUMMARY
-- ============================================================================

-- 14. Get AI summary for a company
SELECT 
    brand_name,
    ai_summary_text,
    ai_summary_updated_at,
    ai_summary_language,
    ai_summary_model_version
FROM companies
WHERE brand_name = 'Simple Life'  -- Change brand name here
  AND ai_summary_text IS NOT NULL;

-- ============================================================================
-- CONSUMER ANALYSIS
-- ============================================================================

-- 15. Top reviewers (consumers with most reviews)
SELECT 
    r.consumer_name,
    r.consumer_country_code,
    COUNT(*) as reviews_given,
    ROUND(AVG(r.rating)::numeric, 2) as avg_rating
FROM reviews r
GROUP BY r.consumer_name, r.consumer_country_code
ORDER BY reviews_given DESC
LIMIT 20;

-- 16. Reviews by country
SELECT 
    c.brand_name,
    r.consumer_country_code,
    COUNT(*) as review_count
FROM reviews r
JOIN companies c ON r.company_id = c.id
GROUP BY c.brand_name, r.consumer_country_code
ORDER BY c.brand_name, review_count DESC;