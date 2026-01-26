#!/usr/bin/env python3
"""
Generate Trustpilot Weekly Reports with Advanced Theme Extraction
Uses PostgreSQL full-text search for optimal performance
"""

from db import Database
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

def extract_themes_from_reviews(db, company_id, week_start, week_end):
    """
    Extract themes using PostgreSQL full-text search with actual keywords from reviews
    Uses word boundaries to prevent false matches (e.g., "car" matching "care")
    """
    
    print("  🔍 Extracting themes from reviews...")
    
    # Get total review counts by sentiment for percentage calculations
    sentiment_counts = db.query("""
        SELECT 
            CASE 
                WHEN rating >= 4 THEN 'positive'
                WHEN rating <= 2 THEN 'negative'
                ELSE 'neutral'
            END as sentiment,
            COUNT(*) as count
        FROM reviews
        WHERE company_id = %(company_id)s
          AND review_date >= %(week_start)s
          AND review_date < %(week_end)s
          AND text IS NOT NULL
        GROUP BY sentiment
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})
    
    sentiment_totals = {s['sentiment']: s['count'] for s in sentiment_counts}
    positive_total = sentiment_totals.get('positive', 0)
    negative_total = sentiment_totals.get('negative', 0)
    neutral_total = sentiment_totals.get('neutral', 0)
    
    if positive_total == 0 and negative_total == 0 and neutral_total == 0:
        return {'positive': [], 'neutral': [], 'negative': []}
    
    # Extract positive themes with word boundary matching (rating >= 4)
    positive_themes = db.query("""
        WITH review_texts AS (
            SELECT 
                id,
                rating,
                LOWER(COALESCE(text_en, text)) as review_text,
                language
            FROM reviews
            WHERE company_id = %(company_id)s
              AND review_date >= %(week_start)s
              AND review_date < %(week_end)s
              AND rating >= 4
              AND text IS NOT NULL
        ),
        topic_matches AS (
            SELECT 
                t.topic_name,
                t.topic_key,
                COUNT(DISTINCT r.id) as mention_count
            FROM topics t
            CROSS JOIN review_texts r
            CROSS JOIN unnest(t.search_terms) as term
            WHERE r.review_text ~ ('(^|[^a-z])' || term || '([^a-z]|$)')
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
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})
    
    # Extract negative themes with word boundary matching (rating <= 2)
    negative_themes = db.query("""
        WITH review_texts AS (
            SELECT 
                id,
                rating,
                LOWER(COALESCE(text_en, text)) as review_text,
                language
            FROM reviews
            WHERE company_id = %(company_id)s
              AND review_date >= %(week_start)s
              AND review_date < %(week_end)s
              AND rating <= 2
              AND text IS NOT NULL
        ),
        topic_matches AS (
            SELECT 
                t.topic_name,
                t.topic_key,
                COUNT(DISTINCT r.id) as mention_count
            FROM topics t
            CROSS JOIN review_texts r
            CROSS JOIN unnest(t.search_terms) as term
            WHERE r.review_text ~ ('(^|[^a-z])' || term || '([^a-z]|$)')
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
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})
    
    # Extract neutral themes (rating = 3)
    neutral_themes = db.query("""
        WITH review_texts AS (
            SELECT 
                id,
                rating,
                LOWER(COALESCE(text_en, text)) as review_text,
                language
            FROM reviews
            WHERE company_id = %(company_id)s
              AND review_date >= %(week_start)s
              AND review_date < %(week_end)s
              AND rating = 3
              AND text IS NOT NULL
        ),
        topic_matches AS (
            SELECT 
                t.topic_name,
                t.topic_key,
                COUNT(DISTINCT r.id) as mention_count
            FROM topics t
            CROSS JOIN review_texts r
            CROSS JOIN unnest(t.search_terms) as term
            WHERE r.review_text ~ ('(^|[^a-z])' || term || '([^a-z]|$)')
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
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})
    
    # Format results - simplified to just topic and count
    positive_formatted = []
    for theme in positive_themes:
        positive_formatted.append({
            'topic': theme['topic_name'],
            'count': theme['mention_count']
        })
    
    negative_formatted = []
    for theme in negative_themes:
        negative_formatted.append({
            'topic': theme['topic_name'],
            'count': theme['mention_count']
        })
    
    neutral_formatted = []
    for theme in neutral_themes:
        neutral_formatted.append({
            'topic': theme['topic_name'],
            'count': theme['mention_count']
        })
    
    print(f"  ✓ Found {len(positive_formatted)} positive, {len(neutral_formatted)} neutral, {len(negative_formatted)} negative themes")
    
    return {
        'positive': positive_formatted[:10],
        'neutral': neutral_formatted[:10],
        'negative': negative_formatted[:10]
    }

def generate_weekly_report(company_name, iso_week):
    """
    Generate comprehensive weekly report for a company
    
    Args:
        company_name: Company domain (e.g., "ketogo.app")
        iso_week: ISO week string (e.g., "2026-W04")
    
    Returns:
        dict: Complete weekly report data
    """
    
    db = Database()
    
    print(f"\n{'='*70}")
    print(f"GENERATING WEEKLY REPORT")
    print(f"{'='*70}\n")
    print(f"Company: {company_name}")
    print(f"Week: {iso_week}\n")
    
    # Get company data
    company = db.query("""
        SELECT *
        FROM companies
        WHERE name = %s
    """, (company_name,))
    
    if not company:
        print(f"❌ Company '{company_name}' not found")
        db.close()
        return None
    
    company = company[0]
    company_id = company['id']
    
    # Parse ISO week
    year, week = iso_week.split('-W')
    year, week = int(year), int(week)
    
    # Calculate week date range (Monday to Sunday inclusive)
    jan4 = datetime(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=7)
    
    print(f"Date range: {week_start.strftime('%Y-%m-%d')} to {(week_end - timedelta(days=1)).strftime('%Y-%m-%d')}\n")
    
    # =========================================================================
    # FETCH DATA
    # =========================================================================
    
    # AI Summary
    ai_summary = db.query("""
        SELECT summary_text, summary_language, model_version, topics, created_at
        FROM ai_summaries
        WHERE company_id = %s
    """, (company_id,))
    
    # Parse topics
    topics_list = []
    if ai_summary and ai_summary[0] and ai_summary[0]['topics']:
        topics_data = ai_summary[0]['topics'] if isinstance(ai_summary[0]['topics'], list) else json.loads(ai_summary[0]['topics'])
        topics_list = [topic.get('topic', topic) if isinstance(topic, dict) else topic for topic in topics_data]
    
    # Parse categories
    categories_list = []
    if company['categories']:
        categories_data = company['categories'] if isinstance(company['categories'], list) else json.loads(company['categories'])
        categories_list = [cat.get('name', cat) if isinstance(cat, dict) else cat for cat in categories_data]
    
    # =========================================================================
    # CURRENT WEEK STATISTICS
    # =========================================================================
    
    print("📊 Calculating week statistics...")
    
    stats = db.query("""
        SELECT 
            COUNT(*) as total_reviews,
            ROUND(AVG(rating)::numeric, 2) as avg_rating,
            SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as neutral_count,
            SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as rating_5,
            SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as rating_4,
            SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as rating_3,
            SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as rating_2,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as rating_1,
            SUM(CASE WHEN reply_message IS NOT NULL THEN 1 ELSE 0 END) as reviews_with_reply,
            SUM(CASE WHEN is_edited = true THEN 1 ELSE 0 END) as reviews_edited,
            SUM(CASE WHEN verified = true THEN 1 ELSE 0 END) as verified_count,
            SUM(CASE WHEN verified = false THEN 1 ELSE 0 END) as organic_count,
            AVG(
                CASE 
                    WHEN reply_date IS NOT NULL AND review_date IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (reply_date - review_date)) / 3600
                    ELSE NULL
                END
            ) as avg_response_hours
        FROM reviews
        WHERE company_id = %s
          AND review_date >= %s
          AND review_date < %s
    """, (company_id, week_start, week_end))
    
    if not stats or stats[0]['total_reviews'] == 0:
        print(f"❌ No reviews found for week {iso_week}")
        db.close()
        return None
    
    stat = stats[0]
    print(f"  ✓ {stat['total_reviews']} reviews this week")
    
    # =========================================================================
    # PREVIOUS WEEK (WoW comparison)
    # =========================================================================
    
    print("📊 Calculating previous week for WoW comparison...")
    
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start
    
    prev_stats = db.query("""
        SELECT 
            COUNT(*) as total_reviews,
            ROUND(AVG(rating)::numeric, 2) as avg_rating
        FROM reviews
        WHERE company_id = %s
          AND review_date >= %s
          AND review_date < %s
    """, (company_id, prev_week_start, prev_week_end))
    
    prev_stat = prev_stats[0] if prev_stats else {'total_reviews': 0, 'avg_rating': None}
    
    # Calculate WoW changes
    wow_volume = stat['total_reviews'] - prev_stat['total_reviews']
    wow_volume_pct = (wow_volume / prev_stat['total_reviews'] * 100) if prev_stat['total_reviews'] > 0 else None
    
    wow_rating = None
    if stat['avg_rating'] and prev_stat['avg_rating']:
        wow_rating = float(stat['avg_rating']) - float(prev_stat['avg_rating'])
    
    # =========================================================================
    # LANGUAGE BREAKDOWN
    # =========================================================================
    
    languages = db.query("""
        SELECT 
            language,
            COUNT(*) as count
        FROM reviews
        WHERE company_id = %s
          AND review_date >= %s
          AND review_date < %s
        GROUP BY language
        ORDER BY count DESC
    """, (company_id, week_start, week_end))
    
    language_breakdown = {lang['language']: lang['count'] for lang in languages} if languages else {}
    
    # =========================================================================
    # THEME EXTRACTION (Advanced)
    # =========================================================================
    
    themes = extract_themes_from_reviews(db, company_id, week_start, week_end)
    
    # =========================================================================
    # TOP COUNTRIES
    # =========================================================================
    
    countries = db.query("""
        SELECT 
            author_country_code,
            COUNT(*) as count
        FROM reviews
        WHERE company_id = %s
          AND review_date >= %s
          AND review_date < %s
          AND author_country_code IS NOT NULL
        GROUP BY author_country_code
        ORDER BY count DESC
        LIMIT 10
    """, (company_id, week_start, week_end))
    
    country_breakdown = [
        {'country': c['author_country_code'], 'review_count': c['count']} 
        for c in countries
    ]
    
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
            # 1. Review Volume
            "review_volume": {
                "total_this_week": stat['total_reviews'],
                "total_last_week": prev_stat['total_reviews'],
                "wow_change": wow_volume,
                "wow_change_pct": round(wow_volume_pct, 2) if wow_volume_pct is not None else None,
                "by_language": language_breakdown,
                "by_country": country_breakdown,
                "by_source": {
                    "verified_invited": stat['verified_count'],
                    "organic": stat['organic_count']
                }
            },
            
            # 2. Rating Performance
            "rating_performance": {
                "avg_rating_this_week": float(stat['avg_rating']) if stat['avg_rating'] else None,
                "avg_rating_last_week": float(prev_stat['avg_rating']) if prev_stat['avg_rating'] else None,
                "wow_change": round(wow_rating, 2) if wow_rating is not None else None
            },
            
            # 3. Sentiment Breakdown
            "sentiment": {
                "positive": {
                    "count": stat['positive_count'],
                    "percentage": round((stat['positive_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0
                },
                "neutral": {
                    "count": stat['neutral_count'],
                    "percentage": round((stat['neutral_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0
                },
                "negative": {
                    "count": stat['negative_count'],
                    "percentage": round((stat['negative_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0
                }
            },
            
            # Rating distribution
            "rating_distribution": {
                "5_stars": stat['rating_5'],
                "4_stars": stat['rating_4'],
                "3_stars": stat['rating_3'],
                "2_stars": stat['rating_2'],
                "1_star": stat['rating_1']
            },
            
            # 4. Brand Response Performance
            "response_performance": {
                "reviews_with_response": stat['reviews_with_reply'],
                "reviews_edited": stat['reviews_edited'],
                "response_rate_pct": round((stat['reviews_with_reply'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0,
                "reviews_without_response": stat['total_reviews'] - stat['reviews_with_reply'],
                "avg_response_time_hours": round(float(stat['avg_response_hours']), 2) if stat['avg_response_hours'] else None,
                "avg_response_time_days": round(float(stat['avg_response_hours']) / 24, 2) if stat['avg_response_hours'] else None
            },
            
            # 5. Content Analysis (Theme Extraction)
            "content_analysis": {
                "positive_themes": themes['positive'],
                "neutral_themes": themes['neutral'],
                "negative_themes": themes['negative']
            }
        }
    }
    
    db.close()
    
    print("\n✅ Report generation complete!\n")
    
    return output

def main():
    """Main entry point"""
    
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python generate_weekly_report.py <company_name> <iso_week>")
        print("")
        print("Examples:")
        print("  python generate_weekly_report.py ketogo.app 2026-W04")
        print("  python generate_weekly_report.py 'simple-life-app.com' 2026-W03")
        sys.exit(1)
    
    company_name = sys.argv[1]
    iso_week = sys.argv[2]
    
    # Validate ISO week format
    if not iso_week.startswith('20') or '-W' not in iso_week:
        print(f"❌ Invalid ISO week format: {iso_week}")
        print("Expected format: YYYY-WNN (e.g., 2026-W04)")
        sys.exit(1)
    
    # Generate report
    report = generate_weekly_report(company_name, iso_week)
    
    if not report:
        sys.exit(1)
    
    # Save to file
    filename = f"weekly_report_{company_name.replace('.', '_')}_{iso_week}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
    
    print(f"📄 Report saved: {filename}")
    
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