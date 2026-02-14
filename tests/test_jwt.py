#!/usr/bin/env python3
"""
JWT Test Suite - Check expiration + test page access
"""

import os
import json
import base64
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


def decode_jwt_payload(jwt_token):
    """Decode JWT payload without verification"""
    try:
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return None


def check_expiration(jwt_token):
    """Check JWT expiration and return days left"""
    
    payload = decode_jwt_payload(jwt_token)
    if not payload or 'exp' not in payload:
        return None
    
    exp_date = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    time_left = exp_date - now
    
    return {
        'payload': payload,
        'issued_at': datetime.fromtimestamp(payload.get('iat', 0), tz=timezone.utc) if 'iat' in payload else None,
        'expires_at': exp_date,
        'time_left': time_left,
        'days_left': time_left.days,
        'hours_left': time_left.seconds // 3600,
        'minutes_left': (time_left.seconds % 3600) // 60,
        'is_valid': time_left.total_seconds() > 0
    }


def test_page_access(jwt_token, company_domain, pages_to_test):
    """Test access to multiple pages"""
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cookie": f"jwt={jwt_token};"
    }
    
    url = f"https://www.trustpilot.com/review/{company_domain}"
    results = []
    
    for page in pages_to_test:
        params = {"page": page}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 404:
                results.append({"page": page, "success": False, "reviews": 0, "reason": "404"})
                continue
            
            if response.status_code != 200:
                results.append({"page": page, "success": False, "reviews": 0, "reason": f"HTTP {response.status_code}"})
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            next_data = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not next_data:
                results.append({"page": page, "success": False, "reviews": 0, "reason": "no_data"})
                continue
            
            data = json.loads(next_data.string)
            reviews = data.get('props', {}).get('pageProps', {}).get('reviews', [])
            
            if reviews:
                results.append({"page": page, "success": True, "reviews": len(reviews)})
            else:
                results.append({"page": page, "success": False, "reviews": 0, "reason": "no_reviews"})
                
        except Exception as e:
            results.append({"page": page, "success": False, "reviews": 0, "reason": str(e)[:50]})
    
    return results


def main(company_domain="ketogo.app", pages_list=[1, 10, 11, 12, 15, 20]):
    """Run complete JWT test suite"""
    
    print("\n" + "="*70)
    print("JWT TEST SUITE")
    print("="*70 + "\n")
    
    # Load JWT
    jwt_token = os.getenv("TRUSTPILOT_JWT")
    
    if not jwt_token or jwt_token == "your.jwt.token":
        print("❌ No valid JWT token found in .env")
        return False
    
    print(f"Token: {jwt_token[:15]}...{jwt_token[-15:]}")
    print(f"Length: {len(jwt_token)} characters\n")
    
    # 1. Check Expiration
    print("="*70)
    print("STEP 1: TOKEN EXPIRATION CHECK")
    print("="*70 + "\n")
    
    exp_info = check_expiration(jwt_token)
    
    if not exp_info:
        print("⚠️  Could not decode token expiration")
    else:
        if exp_info['issued_at']:
            print(f"Issued:  {exp_info['issued_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Expires: {exp_info['expires_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Now:     {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        if exp_info['is_valid']:
            print(f"✅ Token is VALID")
            print(f"⏳ {exp_info['days_left']} days, {exp_info['hours_left']} hours, {exp_info['minutes_left']} minutes remaining")
            
            if exp_info['days_left'] < 7:
                print(f"\n⚠️  WARNING: Expires in less than 7 days!")
            if exp_info['days_left'] < 1:
                print(f"\n🚨 URGENT: Expires in less than 24 hours!")
        else:
            print(f"❌ Token EXPIRED {abs(exp_info['days_left'])} days ago!")
            print(f"🔄 Extract a new JWT from your browser")
            return False
    
    # 2. Test Page Access
    print("\n" + "="*70)
    print("STEP 2: PAGE ACCESS TEST")
    print("="*70 + "\n")
    
    print(f"Testing: {company_domain}")
    print(f"Pages: {pages_list}\n")
    
    results = test_page_access(jwt_token, company_domain, pages_list)
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        if r['success']:
            print(f"  {status} Page {r['page']:2d}: {r['reviews']} reviews")
        else:
            print(f"  {status} Page {r['page']:2d}: {r.get('reason', 'failed')}")
    
    # 3. Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70 + "\n")
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    beyond_10 = [r for r in successful if r['page'] > 10]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    if successful:
        print(f"   Pages: {[r['page'] for r in successful]}")
        print(f"   Total reviews fetched: {sum(r['reviews'] for r in successful)}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        print(f"   Pages: {[r['page'] for r in failed]}")
    
    if beyond_10:
        print(f"\n🎉 JWT WORKING - Accessed {len(beyond_10)} pages beyond page 10!")
        return True
    else:
        print(f"\n❌ JWT LIMITED - Cannot access pages beyond 10")
        return False


if __name__ == "__main__":
    import sys
    
    company = sys.argv[1] if len(sys.argv) > 1 else "ketogo.app"
    
    if len(sys.argv) > 2:
        pages = [int(p) for p in sys.argv[2:]]
        main(company, pages)
    else:
        main(company)