import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json

load_dotenv()

JWT_TOKEN = os.getenv("TRUSTPILOT_JWT")
DOMAIN = "ketogo.app"

print(f"✅ JWT Token: {JWT_TOKEN[:20]}...{JWT_TOKEN[-10:]}")

# Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
    "Cookie": f"jwt={JWT_TOKEN};"
}

# Test pages 11, 12, 13
base_url = f"https://www.trustpilot.com/review/{DOMAIN}"

for page_num in [11, 12, 13]:
    print(f"\n{'='*60}")
    print(f"TESTING PAGE {page_num}")
    print('='*60)
    
    params = {
        "date": "last30days",
        "languages": "all",
        "page": page_num
    }
    
    full_url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    print(f"🔗 URL: {full_url}")
    
    response = requests.get(base_url, params=params, headers=headers, timeout=30)
    print(f"📡 Status: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    next_data = soup.find('script', {'id': '__NEXT_DATA__'})
    
    if not next_data:
        print("❌ No __NEXT_DATA__ found")
        continue
    
    data = json.loads(next_data.string)
    page_props = data.get('props', {}).get('pageProps', {})
    
    print(f"📦 pageProps keys: {list(page_props.keys())[:10]}")
    
    if 'reviews' in page_props:
        reviews = page_props['reviews']
        print(f"✅ Found {len(reviews)} reviews")
        if reviews:
            print(f"   First review ID: {reviews[0].get('id')}")
    else:
        print(f"❌ NO REVIEWS KEY!")
        print(f"   Keys present: {list(page_props.keys())}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)