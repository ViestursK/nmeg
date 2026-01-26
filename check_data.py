#!/usr/bin/env python3
"""
Check Trustpilot database data
"""

from db import Database
from datetime import datetime
import json
import sys

def print_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def export_company_json(company_name):
    """Export company data in JSON format matching desired output"""
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
    
    # Get reviews
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
            print(f"Exporting data for: {company_name}")
            data = export_company_json(company_name)
            if data:
                filename = f"trustpilot_{company_name.replace(' ', '_').lower()}_export.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Exported to: {filename}")
        else:
            print("Usage:")
            print("  python check_data.py              # Show all data")
            print("  python check_data.py export 'Company Name'  # Export to JSON")
    else:
        check_data()