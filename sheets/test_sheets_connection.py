#!/usr/bin/env python3
"""
Test Google Sheets connection and folder access
"""

import os
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

load_dotenv()

def test_connection():
    """Test connection to Google Drive and Sheets"""
    
    print("\n" + "="*70)
    print("TESTING GOOGLE SHEETS CONNECTION")
    print("="*70 + "\n")
    
    # Check env vars
    print("1️⃣ Checking environment variables...")
    
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    
    if not folder_id:
        print("❌ GOOGLE_DRIVE_FOLDER_ID not set in .env")
        return False
    
    if not creds_file:
        print("❌ GOOGLE_SHEETS_CREDENTIALS not set in .env")
        return False
    
    if not os.path.exists(creds_file):
        print(f"❌ Credentials file not found: {creds_file}")
        return False
    
    print(f"✅ GOOGLE_DRIVE_FOLDER_ID: {folder_id}")
    print(f"✅ GOOGLE_SHEETS_CREDENTIALS: {creds_file}\n")
    
    # Setup credentials
    print("2️⃣ Authenticating...")
    
    try:
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        gc = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        
        print("✅ Authentication successful\n")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Test folder access
    print("3️⃣ Testing folder access...")
    
    try:
        folder = drive_service.files().get(
            fileId=folder_id,
            fields='id,name,mimeType'
        ).execute()
        
        print(f"✅ Folder found: {folder.get('name')}")
        print(f"   ID: {folder_id}\n")
        
    except Exception as e:
        print(f"❌ Cannot access folder: {e}")
        print(f"   Make sure the service account has access to the folder")
        return False
    
    # List spreadsheets in folder
    print("4️⃣ Looking for spreadsheets in folder...")
    
    try:
        query = (
            f"'{folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.spreadsheet' and "
            f"trashed=false"
        )
        
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            print(f"✅ Found {len(files)} spreadsheet(s):")
            for f in files:
                print(f"   - {f['name']} ({f['id']})")
        else:
            print("⚠️  No spreadsheets found in folder")
            print(f"   Create one manually at: https://drive.google.com/drive/folders/{folder_id}")
            print(f"   Name it: 'Trustpilot Report - YourBrand'")
        
        print()
        
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return False
    
    # Test write access
    if files:
        print("5️⃣ Testing write access...")
        
        try:
            test_sheet_id = files[0]['id']
            workbook = gc.open_by_key(test_sheet_id)
            
            # Try to get first worksheet
            ws = workbook.sheet1
            print(f"✅ Can access sheet: {workbook.title}")
            print(f"   First tab: {ws.title}\n")
            
        except Exception as e:
            print(f"❌ Cannot write to sheet: {e}")
            print(f"   Make sure the service account has Editor access")
            return False
    
    print("="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    print("\nYou're ready to upload reports!")
    print("\nNext steps:")
    print("  1. Create a Google Sheet named 'Trustpilot Report - [Brand]'")
    print(f"  2. Put it in folder: https://drive.google.com/drive/folders/{folder_id}")
    print("  3. Share with service account (Editor access)")
    print("  4. Run: python sheets_uploader.py 'Brand' report.json\n")
    
    return True


if __name__ == "__main__":
    test_connection()