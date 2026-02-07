#!/usr/bin/env python3
"""
Weekly Report Generator for Trustpilot Data (Refactored)
- Single DB connection (passed in)
- Optimized theme extraction
- Includes AI summary
- Correct week start/end timestamps (full 7 days)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import sys

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def ensure_list(value):
    """Safely convert JSON or list to list"""
    if not value:
        return []
    return value if isinstance(value, list) else json.loads(value)

def count_occurrences(items, key_func):
    """Generic counter helper"""
    counts = {}
    for item in items:
        key = key_func(item)
        counts[key] = counts.get(key, 0) + 1
    return counts

def extract_sentiment_themes(db, company_id, week_start, week_end, rating_filter):
    """
    Extract themes for a specific sentiment using optimized query
    rating_filter: 'positive' (>=4), 'neutral' (=3), or 'negative' (<=2)
    """
    rating_clause = {
        'positive': "rating >= 4",
        'neutral': "rating = 3",
        'negative': "rating <= 2"
    }[rating_filter]

    themes = db.query(f"""
        WITH topic_matches AS (
            SELECT 
                t.topic_name,
                t.topic_key,
                COUNT(DISTINCT r.id) AS mention_count
            FROM topics t
            CROSS JOIN tmp_review_texts r
            CROSS JOIN unnest(t.search_terms) AS term
            WHERE r.{rating_clause}
              AND r.review_text ~ ('(^|[^a-z])' || regexp_replace(term, '[^a-z0-9]', '\\\\\\&', 'g') || '([^a-z]|$)')
            GROUP BY t.topic_name, t.topic_key
        )
        SELECT topic_name, topic_key, mention_count
        FROM topic_matches
        WHERE mention_count > 0
        ORDER BY mention_count DESC
        LIMIT 15;
    """)
    return [{'topic': t['topic_name'], 'count': t['mention_count']} for t in themes[:10]]

def generate_weekly_report(db, company_name, iso_week):
    """Generate weekly report including AI summary"""

    print(f"  📊 {iso_week}...", end=' ', flush=True)

    # --- ISO week parsing and week start/end timestamps ---
    year, week = map(int, iso_week.split('-W'))
    jan4 = datetime(year, 1, 4)
    week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7) - timedelta(seconds=1)
    prev_week_start = week_start - timedelta(days=7)

    # --- Fetch company ---
    company = db.query("SELECT * FROM companies WHERE name = %s", (company_name,))
    if not company:
        print("❌ Company not found")
        return None
    company = company[0]
    company_id = company['id']

    # --- Fetch reviews for current + previous week ---
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
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end, 'prev_week_start': prev_week_start})

    current_week = [r for r in all_reviews if r['period'] == 'current']
    prev_week = [r for r in all_reviews if r['period'] == 'previous']

    if not current_week:
        print("❌ No reviews this week")
        return None

    # --- Aggregate stats ---
    def safe_avg(lst):
        return round(sum(lst)/len(lst), 2) if lst else None

    ratings = [r['rating'] for r in current_week]
    total_reviews = len(current_week)
    avg_rating = safe_avg(ratings)

    sentiment_counts = {
        'positive': sum(1 for r in current_week if r['rating'] >= 4),
        'neutral': sum(1 for r in current_week if r['rating'] == 3),
        'negative': sum(1 for r in current_week if r['rating'] <= 2)
    }

    rating_dist = {i: sum(1 for r in current_week if r['rating'] == i) for i in range(1,6)}
    reviews_with_reply = sum(1 for r in current_week if r['has_reply'])
    reviews_edited = sum(1 for r in current_week if r['is_edited'])
    verified_count = sum(1 for r in current_week if r['verified'])
    organic_count = total_reviews - verified_count

    avg_response_hours = safe_avg([r['response_hours'] for r in current_week if r['response_hours'] is not None])

    # Language & country breakdown
    language_breakdown = count_occurrences(current_week, lambda r: r['language'] or 'unknown')
    country_breakdown = count_occurrences([r for r in current_week if r['author_country_code']], lambda r: r['author_country_code'])
    country_breakdown = sorted([{'country': k, 'review_count': v} for k,v in country_breakdown.items()], key=lambda x: x['review_count'], reverse=True)[:10]

    # WoW comparison
    prev_total = len(prev_week)
    prev_avg_rating = safe_avg([r['rating'] for r in prev_week])
    wow_volume = total_reviews - prev_total
    wow_volume_pct = round((wow_volume / prev_total * 100), 2) if prev_total else None
    wow_rating = round(avg_rating - prev_avg_rating, 2) if prev_avg_rating else None

    # --- Theme extraction using temp table ---
    db.query("""
        CREATE TEMP TABLE IF NOT EXISTS tmp_review_texts AS
        SELECT id, rating, LOWER(COALESCE(text_en, text)) AS review_text
        FROM reviews
        WHERE company_id = %(company_id)s
          AND review_date >= %(week_start)s
          AND review_date < %(week_end)s
          AND text IS NOT NULL
    """, {'company_id': company_id, 'week_start': week_start, 'week_end': week_end})

    positive_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'positive')
    neutral_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'neutral')
    negative_themes = extract_sentiment_themes(db, company_id, week_start, week_end, 'negative')

    db.query("DROP TABLE IF EXISTS tmp_review_texts;")

    # --- AI Summary ---
    ai_data = db.query("""
        SELECT summary_text, summary_language, model_version, topics, created_at
        FROM ai_summaries
        WHERE company_id = %s
    """, (company_id,))

    ai_summary_text = None
    ai_topics = []
    if ai_data:
        ai_summary_text = ai_data[0].get('summary_text')
        topics_raw = ensure_list(ai_data[0].get('topics'))
        ai_topics = [t.get('topic', t) if isinstance(t, dict) else t for t in topics_raw]

    categories_list = ensure_list(company.get('categories'))

    # --- Build report ---
    output = {
        # Identifiers
        "company_id": company_id,
        "company_domain": company["name"],
        "brand_name": company.get("display_name") or company["name"],
        "iso_week": iso_week,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),

        # Ratings & sentiments
        "total_reviews_week": total_reviews,
        "avg_rating": avg_rating,
        "positive_reviews": sentiment_counts['positive'],
        "neutral_reviews": sentiment_counts['neutral'],
        "negative_reviews": sentiment_counts['negative'],
        **{f"rating_{i}": rating_dist[i] for i in range(1,6)},

        # Moderation
        "verified_reviews": verified_count,
        "organic_reviews": organic_count,
        "reviews_with_response": reviews_with_reply,
        "response_rate_pct": round((reviews_with_reply / total_reviews)*100,2) if total_reviews else 0,
        "avg_response_time_hours": avg_response_hours,
        "reviews_edited": reviews_edited,

        # Trustpilot data
        "total_reviews_all_time_tp": company.get("total_reviews"),
        "trust_score": float(company["trust_score"]) if company.get("trust_score") else None,
        "stars": company.get("stars"),
        "is_claimed": company.get("is_claimed"),

        # JSON breakdowns
        "language_breakdown_json": json.dumps(language_breakdown),
        "country_breakdown_json": json.dumps(country_breakdown),
        "positive_themes_json": json.dumps(positive_themes),
        "neutral_themes_json": json.dumps(neutral_themes),
        "negative_themes_json": json.dumps(negative_themes),

        # AI summary
        "ai_summary": ai_summary_text,
        "ai_topics": ai_topics,
        "categories": categories_list,

        # Metadata
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

    print(f"✅ ({total_reviews} reviews)")
    return output

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_weekly_report_optimized.py <company_name> <iso_week>")
        sys.exit(1)

    from db import Database
    company_name, iso_week = sys.argv[1], sys.argv[2]

    # Validate ISO week
    if not iso_week.startswith('20') or '-W' not in iso_week:
        print(f"❌ Invalid ISO week format: {iso_week}")
        sys.exit(1)

    db = Database()
    db.connect()
    report = generate_weekly_report(db, company_name, iso_week)
    db.close()

    if not report:
        sys.exit(1)

    filename = f"weekly_report_{company_name.replace('.', '_')}_{iso_week}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)

    print(f"\n📄 Report saved: {filename}")
    print(f"Total Reviews: {report['total_reviews_week']}")
    print(f"Avg Rating: {report['avg_rating']}/5")
    print(f"Response Rate: {report['response_rate_pct']}%")
    print("\nTop Negative Themes:")
    for theme in json.loads(report['negative_themes_json'])[:5]:
        print(f"  • {theme['topic']}: {theme['count']} mentions")

if __name__ == "__main__":
    main()
