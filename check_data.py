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

def export_company_json(brand_name):
    """Export company data in JSON format matching original scraper output"""
    db = Database()
    
    # Get company data
    company = db.query("""
        SELECT 
            c.*,
            COUNT(r.id) as stored_reviews
        FROM companies c
        LEFT JOIN reviews r ON c.id = r.company_id
        WHERE c.brand_name = %s
        GROUP BY c.id
    """, (brand_name,))
    
    if not company:
        print(f"Company '{brand_name}' not found")
        db.close()
        return None
    
    company = company[0]
    
    # Get top mentions
    mentions = db.query("""
        SELECT mention
        FROM top_mentions
        WHERE company_id = %s
        ORDER BY mention
    """, (company['id'],))
    
    top_mentions = [m['mention'] for m in mentions] if mentions else []
    
    # Get reviews
    reviews = db.query("""
        SELECT 
            review_id,
            consumer_name,
            consumer_id,
            consumer_reviews_count,
            consumer_country_code,
            title,
            text,
            rating,
            published_date,
            updated_date,
            experience_date,
            verified,
            reply_message,
            reply_published_date,
            language
        FROM reviews
        WHERE company_id = %s
        ORDER BY published_date DESC
    """, (company['id'],))
    
    # Format reviews
    formatted_reviews = []
    for r in reviews:
        review_data = {
            "id": r['review_id'],
            "filtered": False,
            "isPending": False,
            "text": r['text'],
            "rating": r['rating'],
            "labels": {
                "merged": None,
                "verification": {
                    "isVerified": r['verified'],
                    "createdDateTime": r['published_date'].isoformat() + 'Z' if r['published_date'] else None,
                    "reviewSourceName": "Organic" if not r['verified'] else "InvitationApi",
                    "verificationSource": "invitation",
                    "verificationLevel": "verified" if r['verified'] else "not-verified",
                    "hasDachExclusion": False
                }
            },
            "title": r['title'],
            "likes": 0,
            "source": "Organic" if not r['verified'] else "InvitationApi",
            "dates": {
                "experiencedDate": r['experience_date'].isoformat() + 'T00:00:00.000Z' if r['experience_date'] else None,
                "publishedDate": r['published_date'].isoformat() + 'Z' if r['published_date'] else None,
                "updatedDate": r['updated_date'].isoformat() + 'Z' if r['updated_date'] else None,
                "submittedDate": None
            },
            "report": None,
            "hasUnhandledReports": False,
            "consumer": {
                "id": r['consumer_id'],
                "displayName": r['consumer_name'],
                "imageUrl": "",
                "numberOfReviews": r['consumer_reviews_count'],
                "countryCode": r['consumer_country_code'],
                "hasImage": False,
                "isVerified": False
            },
            "reply": {
                "message": r['reply_message'],
                "publishedDate": r['reply_published_date'].isoformat() + 'Z' if r['reply_published_date'] else None
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
            "brand_name": company['brand_name'],
            "business_id": company['business_id'],
            "website": company['website'],
            "logo_url": company['logo_url'],
            "total_reviews": company['total_reviews'],
            "trust_score": float(company['trust_score']) if company['trust_score'] else None,
            "stars": int(company['stars']) if company['stars'] else None,
            "is_claimed": company['is_claimed'],
            "categories": company['categories'],
            "ai_summary": {
                "summary": company['ai_summary_text'],
                "updated_at": company['ai_summary_updated_at'].isoformat() + 'Z' if company['ai_summary_updated_at'] else None,
                "language": company['ai_summary_language'],
                "model_version": company['ai_summary_model_version']
            } if company['ai_summary_text'] else None,
            "top_mentions": top_mentions
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
        SELECT id, brand_name, business_id
        FROM companies
        ORDER BY brand_name
    """)
    
    if not companies:
        print("No companies found in database")
        db.close()
        return
    
    for company in companies:
        company_id = company['id']
        brand_name = company['brand_name']
        
        print_section(f"REPORT: {brand_name}")
        
        # =====================================================================
        # BASIC INFO
        # =====================================================================
        basic = db.query("""
            SELECT 
                brand_name,
                business_id,
                website,
                total_reviews as trustpilot_total,
                trust_score,
                stars,
                ai_summary_text,
                ai_summary_updated_at,
                last_scraped_at
            FROM companies
            WHERE id = %s
        """, (company_id,))
        
        if basic:
            b = basic[0]
            print(f"Brand Name: {b['brand_name']}")
            print(f"Website: {b['website']}")
            print(f"Business ID: {b['business_id']}")
            print(f"Trustpilot Total Reviews: {b['trustpilot_total']}")
            print(f"Trust Score: {b['trust_score']}/5")
            print(f"Stars: {b['stars']}")
            print(f"Last Scraped: {b['last_scraped_at']}")
            
            if b['ai_summary_text']:
                print(f"\n📝 AI SUMMARY:")
                print(f"   {b['ai_summary_text'][:300]}...")
                print(f"   Updated: {b['ai_summary_updated_at']}")
        
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
        
        # Reviews this week
        this_week = db.query("""
            SELECT COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
              AND published_date >= NOW() - INTERVAL '7 days'
        """, (company_id,))
        
        this_week_count = this_week[0]['count'] if this_week else 0
        print(f"New Reviews This Week: {this_week_count}")
        
        # Reviews last week (for WoW comparison)
        last_week = db.query("""
            SELECT COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
              AND published_date >= NOW() - INTERVAL '14 days'
              AND published_date < NOW() - INTERVAL '7 days'
        """, (company_id,))
        
        last_week_count = last_week[0]['count'] if last_week else 0
        
        # WoW calculation
        if last_week_count > 0:
            wow_change = this_week_count - last_week_count
            wow_percent = (wow_change / last_week_count) * 100
            print(f"Last Week Reviews: {last_week_count}")
            print(f"Week-over-Week Change: {wow_change:+d} ({wow_percent:+.1f}%)")
        else:
            print(f"Last Week Reviews: {last_week_count}")
            print(f"Week-over-Week Change: N/A (no previous data)")
        
        # Reviews by language
        languages = db.query("""
            SELECT 
                language,
                COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
            GROUP BY language
            ORDER BY count DESC
        """, (company_id,))
        
        if languages:
            print(f"\nReviews by Language:")
            for lang in languages:
                print(f"   {lang['language']}: {lang['count']}")
        
        # Review source (verified vs organic)
        sources = db.query("""
            SELECT 
                verified,
                COUNT(*) as count
            FROM reviews
            WHERE company_id = %s
            GROUP BY verified
        """, (company_id,))
        
        print(f"\nReview Source:")
        for source in sources:
            source_type = "Verified/Invited" if source['verified'] else "Organic"
            percentage = (source['count'] / total_reviews * 100) if total_reviews > 0 else 0
            print(f"   {source_type}: {source['count']} ({percentage:.1f}%)")
        
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
        
        # Average rating this week
        this_week_avg = db.query("""
            SELECT ROUND(AVG(rating)::numeric, 2) as avg_rating
            FROM reviews
            WHERE company_id = %s
              AND published_date >= NOW() - INTERVAL '7 days'
        """, (company_id,))
        
        # Average rating last week
        last_week_avg = db.query("""
            SELECT ROUND(AVG(rating)::numeric, 2) as avg_rating
            FROM reviews
            WHERE company_id = %s
              AND published_date >= NOW() - INTERVAL '14 days'
              AND published_date < NOW() - INTERVAL '7 days'
        """, (company_id,))
        
        if this_week_avg and this_week_avg[0]['avg_rating'] and last_week_avg and last_week_avg[0]['avg_rating']:
            this_avg = float(this_week_avg[0]['avg_rating'])
            last_avg = float(last_week_avg[0]['avg_rating'])
            change = this_avg - last_avg
            print(f"This Week Avg Rating: {this_avg}/5")
            print(f"Last Week Avg Rating: {last_avg}/5")
            print(f"Week-over-Week Change: {change:+.2f}")
        elif this_week_avg and this_week_avg[0]['avg_rating']:
            print(f"This Week Avg Rating: {this_week_avg[0]['avg_rating']}/5")
            print(f"Week-over-Week Change: N/A (no previous data)")
        
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
        
        # Sort in Python instead
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
        # 4. BRAND RESPONSE PERFORMANCE
        # =====================================================================
        print(f"\n{'─'*70}")
        print("4. BRAND RESPONSE PERFORMANCE")
        print(f"{'─'*70}")
        
        response_stats = db.query("""
            SELECT 
                COUNT(*) as total_reviews,
                COUNT(reply_message) as reviews_with_reply,
                ROUND(
                    COUNT(reply_message)::numeric / NULLIF(COUNT(*), 0) * 100, 
                    2
                ) as response_rate
            FROM reviews
            WHERE company_id = %s
        """, (company_id,))
        
        if response_stats:
            stats = response_stats[0]
            print(f"Total Reviews: {stats['total_reviews']}")
            print(f"Reviews with Reply: {stats['reviews_with_reply']}")
            print(f"Response Rate: {stats['response_rate']}%")
        
        # Average response time
        response_time = db.query("""
            SELECT 
                AVG(
                    EXTRACT(EPOCH FROM (reply_published_date - published_date)) / 3600
                ) as avg_hours
            FROM reviews
            WHERE company_id = %s
              AND reply_published_date IS NOT NULL
              AND published_date IS NOT NULL
        """, (company_id,))
        
        if response_time and response_time[0]['avg_hours']:
            hours = float(response_time[0]['avg_hours'])
            if hours < 24:
                print(f"Average Response Time: {hours:.1f} hours")
            else:
                days = hours / 24
                print(f"Average Response Time: {days:.1f} days ({hours:.1f} hours)")
        else:
            print(f"Average Response Time: N/A")
        
        # =====================================================================
        # 5. REVIEW CONTENT ANALYSIS
        # =====================================================================
        print(f"\n{'─'*70}")
        print("5. REVIEW CONTENT ANALYSIS")
        print(f"{'─'*70}")
        
        # Get top mentions
        mentions = db.query("""
            SELECT mention
            FROM top_mentions
            WHERE company_id = %s
            ORDER BY mention
        """, (company_id,))
        
        if mentions:
            all_mentions = [m['mention'] for m in mentions]
            
            # Common positive keywords (heuristic-based)
            positive_keywords = ['great', 'excellent', 'good', 'amazing', 'love', 'best', 
                               'perfect', 'helpful', 'recommend', 'easy', 'fast', 'support']
            negative_keywords = ['scam', 'fraud', 'cancel', 'refund', 'complaint', 'warning',
                               'mistake', 'problem', 'issue', 'bad', 'terrible', 'worst']
            
            positive_themes = [m for m in all_mentions 
                             if any(pos in m.lower() for pos in positive_keywords)]
            negative_themes = [m for m in all_mentions 
                             if any(neg in m.lower() for neg in negative_keywords)]
            
            print(f"\nTop Mentions/Topics ({len(all_mentions)} total):")
            for mention in all_mentions[:10]:
                print(f"   • {mention}")
            
            if positive_themes:
                print(f"\n✅ Positive Themes:")
                for theme in positive_themes[:5]:
                    print(f"   • {theme}")
            
            if negative_themes:
                print(f"\n⚠️  Negative Themes:")
                for theme in negative_themes[:5]:
                    print(f"   • {theme}")
        else:
            print("No top mentions available")
        
        print("\n")
    
    db.close()
    print("✅ Report generation complete!\n")

if __name__ == "__main__":
    # Check if export mode is requested
    if len(sys.argv) > 1:
        if sys.argv[1] == "export" and len(sys.argv) > 2:
            brand_name = sys.argv[2]
            print(f"Exporting data for: {brand_name}")
            data = export_company_json(brand_name)
            if data:
                filename = f"trustpilot_{brand_name.replace(' ', '_').lower()}_export.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Exported to: {filename}")
        else:
            print("Usage:")
            print("  python check_data.py              # Show all data")
            print("  python check_data.py export 'Brand Name'  # Export to JSON")
    else:
        check_data()