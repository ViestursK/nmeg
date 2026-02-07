#!/usr/bin/env python3
"""
Emergency fix: Rebuild raw_data sheet structure
This deletes the broken raw_data sheet and recreates it properly
"""

import sys
import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

def fix_raw_data_structure():
    """Delete and recreate raw_data sheet with proper structure"""
    
    print("\n" + "="*70)
    print("FIXING RAW_DATA SHEET STRUCTURE")
    print("="*70 + "\n")
    
    # Setup credentials
    spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Dashboard")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    
    if not folder_id or not creds_path:
        print("❌ Missing environment variables")
        return False
    
    # Handle relative paths
    if not os.path.isabs(creds_path):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(current_dir) == 'sheets':
            project_root = os.path.dirname(current_dir)
        else:
            project_root = current_dir
        creds_path = os.path.join(project_root, creds_path)
    
    scopes = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    
    # Find spreadsheet
    from googleapiclient.discovery import build
    drive_service = build('drive', 'v3', credentials=creds)
    
    query = (
        f"'{folder_id}' in parents and "
        f"mimeType='application/vnd.google-apps.spreadsheet' and "
        f"name='{spreadsheet_name}' and "
        f"trashed=false"
    )
    
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        supportsAllDrives=True
    ).execute()
    
    files = results.get('files', [])
    
    if not files:
        print(f"❌ Spreadsheet '{spreadsheet_name}' not found")
        return False
    
    spreadsheet_id = files[0]['id']
    workbook = gc.open_by_key(spreadsheet_id)
    
    print(f"✅ Found spreadsheet: {files[0]['name']}")
    
    # Delete old raw_data sheet if it exists
    try:
        old_sheet = workbook.worksheet('raw_data')
        workbook.del_worksheet(old_sheet)
        print("🗑️  Deleted broken raw_data sheet")
    except:
        print("ℹ️  No existing raw_data sheet to delete")
    
    # Create new raw_data sheet
    print("📊 Creating new raw_data sheet...")
    ws = workbook.add_worksheet(title='raw_data', rows=10000, cols=78)
    
    # Write headers
    headers = [
        # Identifiers
        'snapshot_date', 'iso_week', 'week_start', 'week_end',
        'brand_id', 'brand_name', 'website', 'business_id',
        
        # Company Info
        'trust_score', 'total_reviews_alltime', 'is_claimed', 'categories',
        'logo_url', 'star_rating_svg',
        
        # Review Volume
        'reviews_this_week', 'reviews_last_week', 'wow_change', 'wow_change_pct',
        
        # Rating Performance
        'avg_rating', 'avg_rating_last_week', 'rating_wow_change',
        
        # Sentiment
        'positive_count', 'positive_pct',
        'neutral_count', 'neutral_pct',
        'negative_count', 'negative_pct',
        
        # Rating Distribution
        'rating_5_star', 'rating_4_star', 'rating_3_star', 'rating_2_star', 'rating_1_star',
        
        # Response Performance
        'reviews_with_reply', 'response_rate_pct', 'avg_response_hours', 'avg_response_days',
        
        # Sources
        'verified_count', 'organic_count',
        
        # Languages & Countries (top 3)
        'top_language_1', 'top_language_1_count',
        'top_language_2', 'top_language_2_count',
        'top_language_3', 'top_language_3_count',
        'top_country_1', 'top_country_1_count',
        'top_country_2', 'top_country_2_count',
        'top_country_3', 'top_country_3_count',
        
        # Content Analysis (top 5 each)
        'positive_theme_1', 'positive_theme_1_count',
        'positive_theme_2', 'positive_theme_2_count',
        'positive_theme_3', 'positive_theme_3_count',
        'negative_theme_1', 'negative_theme_1_count',
        'negative_theme_2', 'negative_theme_2_count',
        'negative_theme_3', 'negative_theme_3_count',
        
        # AI Summary
        'ai_summary',
        
        # Metadata
        'generated_at'
    ]
    
    print(f"📝 Writing {len(headers)} column headers...")
    ws.update('A1', [headers])
    
    # Format header row
    ws.format('A1:BZ1', {
        'textFormat': {'bold': True, 'fontSize': 10},
        'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
        'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
        'horizontalAlignment': 'CENTER'
    })
    
    ws.freeze(rows=1)
    
    print("\n" + "="*70)
    print("✅ RAW_DATA SHEET FIXED")
    print("="*70)
    print(f"\n📊 Verification:")
    print(f"   • A1 = {headers[0]}")
    print(f"   • B1 = {headers[1]}")
    print(f"   • F1 = {headers[5]}")
    print(f"   • O1 = {headers[14]}")
    print(f"\n🔗 {files[0]['name']}")
    print(f"   https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    print(f"\n🎯 Next step:")
    print(f"   Run: python sheets/test.py")
    print(f"   This will re-upload your data with proper structure\n")
    
    return True


if __name__ == "__main__":
    success = fix_raw_data_structure()
    sys.exit(0 if success else 1)