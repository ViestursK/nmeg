#!/usr/bin/env python3
"""
Optimized Weekly Report Generator for Trustpilot Data
- Single DB connection (passed in)
- Temp table for theme extraction (1 review scan instead of 3)
- Combined queries (stats + language + country in one scan)
- Combined current + previous week fetch
- Refactored theme extraction (no duplication)
"""

from datetime import datetime, timedelta
from decimal import Decimal
import json
import sys

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def ensure_list(value):
    """Safely convert JSON or list to list"""
    if not value:
        return []
    return value if isinstance(value, list) else json.loads(value)

def extract_sentiment_themes(db, company_id, week_start, week_end, rating_filter):
    """
    Extract themes for a specific sentiment using optimized query
    rating_filter: 'positive' (>=4), 'neutral' (=3), or 'negative' (<=2)
    Uses temp table that's already created
    """
    
    if rating_filter == 'positive':
        rating_clause = "rating >= 4"
    elif rating_filter == 'neutral':
        rating_clause = "rating = 3"
    else:  # negative
        rating_clause = "rating <= 2"
    
    themes = db.query(f"""
        WITH topic_matches AS (
            SELECT 
                t.topic_name,
                t.topic_key,
                COUNT(DISTINCT r.id) as mention_count
            FROM topics t
            CROSS JOIN tmp_review_texts r
            CROSS JOIN unnest(t.search_terms) as term
            WHERE r.{rating_clause}
              AND r.review_text ~ ('(^|[^a-z])' || regexp_replace(term, '[^a-z0-9]', '\\\\\\&', 'g') || '([^a-z]|$)')
            GROUP BY t.topic_name, t.topic_key
        )
        SELECT 
            topic_name,
            topic_key,
            mention_count
        FROM topic_matches
        WHERE mention_count > 0
        ORDER BY mention_count DESC
        LIMIT 15;
    """)
    
    return [{'topic': theme['topic_name'], 'count': theme['mention_count']} for theme in themes[:10]]

def generate_weekly_report(db, company_name, iso_week):
    """
    Generate comprehensive weekly report for a company
    
    Args:
        db: Shared Database connection instance
        company_name: Company domain (e.g., "ketogo.app")
        iso_week: ISO week string (e.g., "2026-W04")
    
    Returns:
        dict: Complete weekly report data
    """
    
    print(f"  📊 {iso_week}...", end=' ', flush=True)
    
    # Parse ISO week
    year, week = iso_week.split('-W')
    year, week = int(year), int(week)
    
    # Calculate week date range (Monday to Sunday inclusive)
    jan4 = datetime(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=7)
    prev_week_start = week_start - timedelta(days=7)
    
    # Get company data
    company = db.query("""
        SELECT *
        FROM companies
        WHERE name = %s
    """, (company_name,))
    
    if not company:
        print(f"❌ Not found")
        return None
    
    company = company[0]
    company_id = company['id']
    
    # =========================================================================
    # OPTIMIZATION 1: Single scan for ALL base metrics
    # Fetches current + previous week data + language + country + response times
    # =========================================================================
    
    all_reviews = db.query("""
        SELECT
            CASE
                WHEN review_date >= %(week_start)s THEN 'current'
                WHEN review_date >= %(prev_week_start)s THEN 'previous'
            END AS period,
            rating,
            language,
            author_country_code,
            verified,
            reply_message IS NOT NULL AS has_reply,
            is_edited,
            CASE 
                WHEN reply_date IS NOT NULL AND review_date IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (reply_date - review_date)) / 3600
                ELSE NULL
            END AS response_hours
        FROM reviews
        WHERE company_id = %(company_id)s
          AND review_date >= %(prev_week_start)s
          AND review_date < %(week_end)s
    """, {
        'company_id': company_id,
        'week_start': week_start,
        'week_end': week_end,
        'prev_week_start': prev_week_start
    })
    
    # Aggregate in Python (faster than multiple DB queries)
    current_week = [r for r in all_reviews if r['period'] == 'current']
    prev_week = [r for r in all_reviews if r['period'] == 'previous']
    
    if not current_week:
        print(f"❌ No data")
        return None
    
    # Current week stats
    total_reviews = len(current_week)
    avg_rating = round(sum(r['rating'] for r in current_week) / total_reviews, 2)
    
    positive_count = sum(1 for r in current_week if r['rating'] >= 4)
    neutral_count = sum(1 for r in current_week if r['rating'] == 3)
    negative_count = sum(1 for r in current_week if r['rating'] <= 2)
    
    rating_5 = sum(1 for r in current_week if r['rating'] == 5)
    rating_4 = sum(1 for r in current_week if r['rating'] == 4)
    rating_3 = sum(1 for r in current_week if r['rating'] == 3)
    rating_2 = sum(1 for r in current_week if r['rating'] == 2)
    rating_1 = sum(1 for r in current_week if r['rating'] == 1)
    
    reviews_with_reply = sum(1 for r in current_week if r['has_reply'])
    reviews_edited = sum(1 for r in current_week if r['is_edited'])
    verified_count = sum(1 for r in current_week if r['verified'])
    organic_count = sum(1 for r in current_week if not r['verified'])
    
    response_times = [r['response_hours'] for r in current_week if r['response_hours'] is not None]
    avg_response_hours = round(sum(response_times) / len(response_times), 2) if response_times else None
    
    # Language breakdown
    language_breakdown = {}
    for r in current_week:
        lang = r['language'] or 'unknown'
        language_breakdown[lang] = language_breakdown.get(lang, 0) + 1
    
    # Country breakdown
    country_counts = {}
    for r in current_week:
        if r['author_country_code']:
            country_counts[r['author_country_code']] = country_counts.get(r['author_country_code'], 0) + 1
    
    country_breakdown = [
        {'country': code, 'review_count': count}
        for code, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]
    
    # Previous week stats
    prev_total = len(prev_week)
    prev_avg_rating = round(sum(r['rating'] for r in prev_week) / prev_total, 2) if prev_week else None
    
    wow_volume = total_reviews - prev_total
    wow_volume_pct = round((wow_volume / prev_total * 100), 2) if prev_total > 0 else None
    wow_rating = round(avg_rating - prev_avg_rating, 2) if prev_avg_rating else None
    
    # =========================================================================
    # OPTIMIZATION 2: Theme extraction with temp table (single review scan)
    # =========================================================================
    
    # Create temp table once
    db.query("""
        CREATE TEMP TABLE IF NOT EXISTS tmp_review_texts AS
        SELECT
            id,
            rating,
            LOWER(COALESCE(text_en, text)) AS review_text
        FROM reviews
        WHERE company_id = %(company_id)s
          AND review_date >= %(week_start)s
          AND review_date < %(week_end)s
          AND text IS NOT NULL;
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})
    
    # Extract themes (reuses temp table)
    positive_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'positive')
    neutral_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'neutral')
    negative_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'negative')
    
    # Cleanup temp table
    db.query("DROP TABLE IF EXISTS tmp_review_texts;")
    
    # =========================================================================
    # AI Summary & Topics (single query each)
    # =========================================================================
    
    ai_summary = db.query("""
        SELECT summary_text, summary_language, model_version, topics, created_at
        FROM ai_summaries
        WHERE company_id = %s
    """, (company_id,))
    
    topics_list = []
    if ai_summary and ai_summary[0] and ai_summary[0]['topics']:
        topics_data = ensure_list(ai_summary[0]['topics'])
        topics_list = [topic.get('topic', topic) if isinstance(topic, dict) else topic for topic in topics_data]
    
    categories_list = ensure_list(company['categories'])
    
    # =========================================================================
    # BUILD OUTPUT
    # =========================================================================
    
    output = {
        "company": {
            "brand_name": company['display_name'] or company['name'],
            "business_id": company['business_id'],
            "website": company['website_url'],
            "logo_url": company['logo_url'],
            "star_rating_svg": company['star_rating_svg'],
            "total_reviews_all_time": company['total_reviews'],
            "trust_score": float(company['trust_score']) if company['trust_score'] else None,
            "stars": company['stars'],
            "is_claimed": company['is_claimed'],
            "categories": categories_list,
            "ai_summary": {
                "summary_text": ai_summary[0]['summary_text'] if ai_summary and ai_summary[0] and ai_summary[0]['summary_text'] else None,
                "updated_at": ai_summary[0]['created_at'].isoformat() + 'Z' if ai_summary and ai_summary[0] else None
            } if (ai_summary and ai_summary[0] and ai_summary[0]['summary_text']) else None,
            "top_mentions_overall": topics_list
        },
        
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "iso_week": iso_week,
            "week_start": week_start.strftime('%Y-%m-%d'),
            "week_end": (week_end - timedelta(days=1)).strftime('%Y-%m-%d')
        },
        
        "week_stats": {
            "review_volume": {
                "total_this_week": total_reviews,
                "total_last_week": prev_total,
                "wow_change": wow_volume,
                "wow_change_pct": wow_volume_pct,
                "by_language": language_breakdown,
                "by_country": country_breakdown,
                "by_source": {
                    "verified_invited": verified_count,
                    "organic": organic_count
                }
            },
            
            "rating_performance": {
                "avg_rating_this_week": avg_rating,
                "avg_rating_last_week": prev_avg_rating,
                "wow_change": wow_rating
            },
            
            "sentiment": {
                "positive": {
                    "count": positive_count,
                    "percentage": round((positive_count / total_reviews * 100), 2)
                },
                "neutral": {
                    "count": neutral_count,
                    "percentage": round((neutral_count / total_reviews * 100), 2)
                },
                "negative": {
                    "count": negative_count,
                    "percentage": round((negative_count / total_reviews * 100), 2)
                }
            },
            
            "rating_distribution": {
                "5_stars": rating_5,
                "4_stars": rating_4,
                "3_stars": rating_3,
                "2_stars": rating_2,
                "1_star": rating_1
            },
            
            "response_performance": {
                "reviews_with_response": reviews_with_reply,
                "reviews_edited": reviews_edited,
                "response_rate_pct": round((reviews_with_reply / total_reviews * 100), 2),
                "reviews_without_response": total_reviews - reviews_with_reply,
                "avg_response_time_hours": avg_response_hours,
                "avg_response_time_days": round(avg_response_hours / 24, 2) if avg_response_hours else None
            },
            
            "content_analysis": {
                "positive_themes": positive_themes,
                "neutral_themes": neutral_themes,
                "negative_themes": negative_themes
            }
        }
    }
    
    print(f"✅ ({total_reviews} reviews)")
    
    return output

def main():
    """Main entry point for standalone usage"""
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python generate_weekly_report_optimized.py <company_name> <iso_week>")
        print("")
        print("Examples:")
        print("  python generate_weekly_report_optimized.py ketogo.app 2026-W04")
        sys.exit(1)
    
    from db import Database
    
    company_name = sys.argv[1]
    iso_week = sys.argv[2]
    
    # Validate ISO week format
    if not iso_week.startswith('20') or '-W' not in iso_week:
        print(f"❌ Invalid ISO week format: {iso_week}")
        print("Expected format: YYYY-WNN (e.g., 2026-W04)")
        sys.exit(1)
    
    # Generate report with shared connection
    db = Database()
    db.connect()
    
    report = generate_weekly_report(db, company_name, iso_week)
    
    db.close()
    
    if not report:
        sys.exit(1)
    
    # Save to file
    filename = f"weekly_report_{company_name.replace('.', '_')}_{iso_week}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
    
    print(f"\n📄 Report saved: {filename}")
    
    # Print summary
    print("\n" + "="*70)
    print("REPORT SUMMARY")
    print("="*70)
    print(f"Week: {iso_week}")
    print(f"Total Reviews: {report['week_stats']['review_volume']['total_this_week']}")
    print(f"Avg Rating: {report['week_stats']['rating_performance']['avg_rating_this_week']}/5")
    print(f"Response Rate: {report['week_stats']['response_performance']['response_rate_pct']}%")
    print(f"\nTop Negative Themes:")
    for theme in report['week_stats']['content_analysis']['negative_themes'][:5]:
        print(f"  • {theme['topic']}: {theme['count']} mentions")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()