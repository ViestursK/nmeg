#!/usr/bin/env python3
"""
Check Trustpilot database data
"""

from db import Database
from datetime import datetime
from decimal import Decimal
import json
import sys

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def print_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def export_company_json(company_name, iso_week=None):
    """
    Export company data in JSON format
    
    Args:
        company_name: Company domain name  
        iso_week: Optional ISO week (e.g., "2026-W04") for weekly stats only
    """
    db = Database()
    
    # Get company data with all metadata
    company = db.query("""
        SELECT *
        FROM companies
        WHERE name = %s
    """, (company_name,))
    
    if not company:
        print(f"Company '{company_name}' not found")
        db.close()
        return None
    
    company = company[0]
    
    # Get AI summary
    ai_summary = db.query("""
        SELECT summary_text, summary_language, model_version, topics, created_at
        FROM ai_summaries
        WHERE company_id = %s
    """, (company['id'],))
    
    # Parse topics from JSONB
    topics_list = []
    if ai_summary and ai_summary[0]['topics']:
        import json as json_lib
        topics_data = ai_summary[0]['topics'] if isinstance(ai_summary[0]['topics'], list) else json_lib.loads(ai_summary[0]['topics'])
        topics_list = [topic.get('topic', topic) if isinstance(topic, dict) else topic for topic in topics_data]
    
    # Parse categories
    categories_list = []
    if company['categories']:
        import json as json_lib
        categories_data = company['categories'] if isinstance(company['categories'], list) else json_lib.loads(company['categories'])
        categories_list = [cat.get('name', cat) if isinstance(cat, dict) else cat for cat in categories_data]
    
    # If iso_week provided, generate weekly snapshot stats only
    if iso_week:
        from datetime import datetime as dt, timedelta
        
        # Parse ISO week
        year, week = iso_week.split('-W')
        year, week = int(year), int(week)
        
        # Calculate week date range (Monday to Sunday inclusive)
        jan4 = dt(year, 1, 4)
        week_start = jan4 - timedelta(days=jan4.weekday()) + timedelta(weeks=week-1)
        week_end = week_start + timedelta(days=7)  # Full 7 days (Monday 00:00 to Monday 00:00 next week)
        
        # Get current week stats
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
        """, (company['id'], week_start, week_end))
        
        if not stats or stats[0]['total_reviews'] == 0:
            print(f"No reviews found for week {iso_week}")
            db.close()
            return None
        
        stat = stats[0]
        
        # Get previous week stats for WoW comparison
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
        """, (company['id'], prev_week_start, prev_week_end))
        
        prev_stat = prev_stats[0] if prev_stats else {'total_reviews': 0, 'avg_rating': None}
        
        # Calculate WoW changes
        wow_volume = stat['total_reviews'] - prev_stat['total_reviews']
        wow_volume_pct = (wow_volume / prev_stat['total_reviews'] * 100) if prev_stat['total_reviews'] > 0 else None
        
        wow_rating = None
        if stat['avg_rating'] and prev_stat['avg_rating']:
            wow_rating = float(stat['avg_rating']) - float(prev_stat['avg_rating'])
        
        # Get language breakdown
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
        """, (company['id'], week_start, week_end))
        
        language_breakdown = {lang['language']: lang['count'] for lang in languages} if languages else {}
        
        # Get top positive and negative themes (from review text analysis)
        # For now, we'll extract this from top_mentions if available, or leave as placeholder
        positive_themes = []
        negative_themes = []
        
        # Try to categorize topics from AI summary
        if topics_list:
            # Simple heuristic - topics with certain keywords
            positive_keywords = ['great', 'excellent', 'good', 'amazing', 'helpful', 'support', 'recommend']
            negative_keywords = ['scam', 'fraud', 'cancel', 'refund', 'complaint', 'warning', 'problem']
            
            for topic in topics_list:
                topic_lower = topic.lower()
                if any(pos in topic_lower for pos in positive_keywords):
                    positive_themes.append(topic)
                elif any(neg in topic_lower for neg in negative_keywords):
                    negative_themes.append(topic)
        
        # Build weekly snapshot output
        output = {
            "company": {
                "brand_name": company['display_name'] or company['name'],
                "business_id": company['business_id'],
                "website": company['website_url'],
                "logo_url": company['logo_url'],
                "total_reviews": company['total_reviews'],
                "trust_score": float(company['trust_score']) if company['trust_score'] else None,
                "stars": company['stars'],
                "is_claimed": company['is_claimed'],
                "categories": categories_list,
                "ai_summary": {
                    "summary": ai_summary[0]['summary_text'],
                    "updated_at": ai_summary[0]['created_at'].isoformat() + 'Z',
                    "language": ai_summary[0]['summary_language'],
                    "model_version": ai_summary[0]['model_version']
                } if ai_summary and ai_summary[0]['summary_text'] else None,
                "top_mentions": topics_list
            },
            "week_stats": {
                "iso_week": iso_week,
                "week_start": week_start.strftime('%Y-%m-%d'),
                "week_end": (week_end - timedelta(days=1)).strftime('%Y-%m-%d'),  # Display as Sunday
                
                # 1. Review Volume
                "review_volume": {
                    "total_this_week": stat['total_reviews'],
                    "total_last_week": prev_stat['total_reviews'],
                    "wow_change": wow_volume,
                    "wow_change_pct": round(wow_volume_pct, 2) if wow_volume_pct is not None else None,
                    "by_language": language_breakdown,
                    "by_source": {
                        "verified_invited": stat['verified_count'],
                        "organic": stat['organic_count']
                    }
                },
                
                # 2. Rating Performance
                "rating_performance": {
                    "avg_rating": float(stat['avg_rating']) if stat['avg_rating'] else None,
                    "avg_rating_last_week": float(prev_stat['avg_rating']) if prev_stat['avg_rating'] else None,
                    "wow_change": round(wow_rating, 2) if wow_rating is not None else None
                },
                
                # 3. Sentiment Breakdown
                "sentiment": {
                    "positive": stat['positive_count'],
                    "neutral": stat['neutral_count'],
                    "negative": stat['negative_count'],
                    "positive_pct": round((stat['positive_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0,
                    "neutral_pct": round((stat['neutral_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0,
                    "negative_pct": round((stat['negative_count'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0
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
                    "response_rate_pct": round((stat['reviews_with_reply'] / stat['total_reviews'] * 100), 2) if stat['total_reviews'] > 0 else 0,
                    "reviews_with_response": stat['reviews_with_reply'],
                    "reviews_without_response": stat['total_reviews'] - stat['reviews_with_reply'],
                    "avg_response_time_hours": round(stat['avg_response_hours'], 2) if stat['avg_response_hours'] else None,
                    "avg_response_time_days": round(stat['avg_response_hours'] / 24, 2) if stat['avg_response_hours'] else None
                },
                
                # 5. Review Content Analysis
                "content_analysis": {
                    "positive_themes": positive_themes[:5] if positive_themes else [],
                    "negative_themes": negative_themes[:5] if negative_themes else [],
                    "note": "Themes extracted from AI summary topics. For deeper analysis, implement NLP on review text."
                }
            },
            "extraction_date": datetime.now().isoformat()
        }
        
        db.close()
        return output
    
    # Otherwise, export all reviews
    reviews = db.query("""
        SELECT 
            review_id, rating, title, text, 
            author_name, author_id, author_country_code, author_review_count,
            review_date, experience_date, verified, language,
            reply_message, reply_date, likes, source, labels
        FROM reviews
        WHERE company_id = %s
        ORDER BY review_date DESC
    """, (company['id'],))
    
    # Format reviews
    formatted_reviews = []
    for r in reviews:
        import json as json_lib
        labels = r['labels'] if isinstance(r['labels'], dict) else json_lib.loads(r['labels'] or '{}')
        
        # Calculate ISO week from review_date
        iso_week = None
        if r['review_date']:
            iso_year, iso_week_num, _ = r['review_date'].isocalendar()
            iso_week = f"{iso_year}-W{iso_week_num:02d}"
        
        review_data = {
            "id": r['review_id'],
            "filtered": False,
            "isPending": False,
            "text": r['text'],
            "rating": r['rating'],
            "labels": labels,
            "title": r['title'],
            "likes": r['likes'] or 0,
            "source": r['source'],
            "iso_week": iso_week,
            "dates": {
                "experiencedDate": r['experience_date'].isoformat() + 'T00:00:00.000Z' if r['experience_date'] else None,
                "publishedDate": r['review_date'].isoformat() + 'Z' if r['review_date'] else None,
                "updatedDate": None,
                "submittedDate": None
            },
            "report": None,
            "hasUnhandledReports": False,
            "consumer": {
                "id": r['author_id'],
                "displayName": r['author_name'],
                "imageUrl": "",
                "numberOfReviews": r['author_review_count'] or 0,
                "countryCode": r['author_country_code'],
                "hasImage": False,
                "isVerified": False
            },
            "reply": {
                "message": r['reply_message'],
                "publishedDate": r['reply_date'].isoformat() + 'Z' if r['reply_date'] else None
            } if r['reply_message'] else None,
            "consumersReviewCountOnSameDomain": 1,
            "consumersReviewCountOnSameLocation": None,
            "productReviews": [],
            "language": r['language'],
            "location": None
        }
        formatted_reviews.append(review_data)
    
    # Build final JSON structure
    output = {
        "company": {
            "brand_name": company['display_name'] or company['name'],
            "business_id": company['business_id'],
            "website": company['website_url'],
            "logo_url": company['logo_url'],
            "total_reviews": company['total_reviews'],
            "trust_score": float(company['trust_score']) if company['trust_score'] else None,
            "stars": company['stars'],
            "is_claimed": company['is_claimed'],
            "categories": categories_list,
            "ai_summary": {
                "summary": ai_summary[0]['summary_text'],
                "updated_at": ai_summary[0]['created_at'].isoformat() + 'Z',
                "language": ai_summary[0]['summary_language'],
                "model_version": ai_summary[0]['model_version']
            } if ai_summary and ai_summary[0]['summary_text'] else None,
            "top_mentions": topics_list
        },
        "reviews": formatted_reviews,
        "extraction_date": datetime.now().isoformat(),
        "total_reviews_extracted": len(formatted_reviews)
    }
    
    db.close()
    return output

def check_data():
    """Generate comprehensive report statistics for all brands"""
    db = Database()
    
    # Get all companies
    companies = db.query("""
        SELECT id, name, created_at
        FROM companies
        ORDER BY name
    """)
    
    if not companies:
        print("No companies found in database")
        db.close()
        return
    
    for company in companies:
        company_id = company['id']
        company_name = company['name']
        
        print_section(f"REPORT: {company_name}")
        
        # =====================================================================
        # BASIC INFO
        # =====================================================================
        print(f"Company Name: {company_name}")
        print(f"Created: {company['created_at']}")
        
        # =====================================================================
        # 1. REVIEW VOLUME
        # =====================================================================
        print(f"\n{'─'*70}")
        print("1. REVIEW VOLUME")
        print(f"{'─'*70}")
        
        # Total reviews stored
        total = db.query("""
            SELECT COUNT(*) as total
            FROM reviews
            WHERE company_id = %s
        """, (company_id,))
        
        total_reviews = total[0]['total'] if total else 0
        print(f"Total Reviews Stored: {total_reviews}")
        
        # Reviews by week
        weekly = db.query("""
            SELECT 
                TO_CHAR(review_date, 'IYYY-"W"IW') as week,
                COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
              AND review_date IS NOT NULL
            GROUP BY TO_CHAR(review_date, 'IYYY-"W"IW')
            ORDER BY week DESC
            LIMIT 10
        """, (company_id,))
        
        if weekly:
            print(f"\nReviews by Week (last 10):")
            for w in weekly:
                print(f"   {w['week']}: {w['count']} reviews")
        
        # =====================================================================
        # 2. RATING PERFORMANCE
        # =====================================================================
        print(f"\n{'─'*70}")
        print("2. RATING PERFORMANCE")
        print(f"{'─'*70}")
        
        # Average rating
        avg_rating = db.query("""
            SELECT 
                ROUND(AVG(rating)::numeric, 2) as avg_rating,
                COUNT(*) as total
            FROM reviews
            WHERE company_id = %s
        """, (company_id,))
        
        if avg_rating and avg_rating[0]['avg_rating']:
            print(f"Average Star Rating: {avg_rating[0]['avg_rating']}/5 (from {avg_rating[0]['total']} reviews)")
        
        # =====================================================================
        # 3. SENTIMENT BREAKDOWN
        # =====================================================================
        print(f"\n{'─'*70}")
        print("3. SENTIMENT BREAKDOWN")
        print(f"{'─'*70}")
        
        sentiment = db.query("""
            SELECT 
                CASE 
                    WHEN rating >= 4 THEN 'Positive'
                    WHEN rating = 3 THEN 'Neutral'
                    ELSE 'Negative'
                END as sentiment,
                COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
            GROUP BY 
                CASE 
                    WHEN rating >= 4 THEN 'Positive'
                    WHEN rating = 3 THEN 'Neutral'
                    ELSE 'Negative'
                END
        """, (company_id,))
        
        # Sort in Python
        sentiment_order = {'Positive': 1, 'Neutral': 2, 'Negative': 3}
        if sentiment:
            sentiment = sorted(sentiment, key=lambda x: sentiment_order.get(x['sentiment'], 4))
        
        if sentiment:
            for s in sentiment:
                percentage = (s['count'] / total_reviews * 100) if total_reviews > 0 else 0
                emoji = "😊" if s['sentiment'] == 'Positive' else "😐" if s['sentiment'] == 'Neutral' else "😞"
                print(f"{emoji} {s['sentiment']}: {s['count']} ({percentage:.1f}%)")
        
        # Detailed rating breakdown
        rating_dist = db.query("""
            SELECT 
                rating,
                COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
            GROUP BY rating
            ORDER BY rating DESC
        """, (company_id,))
        
        print(f"\nDetailed Rating Distribution:")
        for rating in rating_dist:
            stars = "⭐" * rating['rating']
            percentage = (rating['count'] / total_reviews * 100) if total_reviews > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"   {stars} ({rating['rating']}): {rating['count']:4d} ({percentage:5.1f}%) {bar}")
        
        # =====================================================================
        # 4. RECENT REVIEWS
        # =====================================================================
        print(f"\n{'─'*70}")
        print("4. RECENT REVIEWS (Last 5)")
        print(f"{'─'*70}")
        
        recent = db.query("""
            SELECT 
                title,
                rating,
                author_name,
                review_date
            FROM reviews
            WHERE company_id = %s
            ORDER BY review_date DESC
            LIMIT 5
        """, (company_id,))
        
        for rev in recent:
            date = rev['review_date'].strftime('%Y-%m-%d') if rev['review_date'] else 'N/A'
            title = (rev['title'] or 'No title')[:50]
            stars = "⭐" * (rev['rating'] or 0)
            print(f"   [{date}] {stars} - {title} ({rev['author_name']})")
        
        print("\n")
    
    db.close()
    print("✅ Report generation complete!\n")

if __name__ == "__main__":
    # Check if export mode is requested
    if len(sys.argv) > 1:
        if sys.argv[1] == "export" and len(sys.argv) > 2:
            company_name = sys.argv[2]
            iso_week = sys.argv[3] if len(sys.argv) > 3 else None
            
            if iso_week:
                print(f"Exporting weekly stats for: {company_name} (Week: {iso_week})")
                data = export_company_json(company_name, iso_week)
                if data:
                    filename = f"trustpilot_{company_name.replace(' ', '_').lower()}_{iso_week}_stats.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
                    print(f"✅ Exported to: {filename}")
            else:
                print(f"Exporting all data for: {company_name}")
                data = export_company_json(company_name)
                if data:
                    filename = f"trustpilot_{company_name.replace(' ', '_').lower()}_export.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False, cls=DecimalEncoder)
                    print(f"✅ Exported to: {filename}")
        else:
            print("Usage:")
            print("  python check_data_weekly.py                           # Show all data")
            print("  python check_data_weekly.py export 'Company Name'     # Export all reviews")
            print("  python check_data_weekly.py export 'Company Name' '2026-W04'  # Export weekly stats")
    else:
        check_data()