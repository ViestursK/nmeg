#!/usr/bin/env python3
"""
Final diagnostic - check Sheets API directly and workspace limits
"""

import os
import sys
from dotenv import load_dotenv
import json

load_dotenv()

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def final_diagnostic():
    """Check Sheets API and workspace settings"""
    
    print("\n" + "="*70)
    print("FINAL DIAGNOSTIC - SHEETS API")
    print("="*70 + "\n")
    
    creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
    # Load credentials JSON to check account type
    print("📋 CREDENTIALS ANALYSIS")
    print("-"*70)
    
    with open(creds_path, 'r') as f:
        creds_data = json.load(f)
    
    print(f"Project ID: {creds_data.get('project_id')}")
    print(f"Client Email: {creds_data.get('client_email')}")
    print(f"Account type: {creds_data.get('type')}")
    
    # Check if it's a workspace account
    email = creds_data.get('client_email', '')
    if 'gserviceaccount.com' in email:
        print(f"✅ Valid service account")
    
    # Setup services
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
    )
    
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    # Count ALL spreadsheets accessible to this service account
    print("\n\n📊 SPREADSHEET COUNT")
    print("-"*70)
    
    try:
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            fields='files(id, name, owners)',
            pageSize=1000
        ).execute()
        
        sheets = results.get('files', [])
        print(f"Total spreadsheets visible to service account: {len(sheets)}")
        
        if sheets:
            print("\nFirst 10 sheets:")
            for sheet in sheets[:10]:
                owner = sheet.get('owners', [{}])[0].get('emailAddress', 'Unknown')
                print(f"  - {sheet.get('name')} (owner: {owner})")
        
    except Exception as e:
        print(f"Error listing sheets: {e}")
    
    # Try to create spreadsheet via Sheets API instead of Drive API
    print("\n\n🧪 TESTING SHEETS API DIRECTLY")
    print("-"*70)
    
    try:
        print("Attempting to create spreadsheet via Sheets API...")
        
        spreadsheet = {
            'properties': {
                'title': 'TEST via Sheets API'
            }
        }
        
        result = sheets_service.spreadsheets().create(
            body=spreadsheet
        ).execute()
        
        spreadsheet_id = result['spreadsheetId']
        print(f"✅ SUCCESS via Sheets API! ID: {spreadsheet_id}")
        print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        # Now try to move it to the folder
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if folder_id:
            print(f"\nMoving to folder {folder_id}...")
            try:
                drive_service.files().update(
                    fileId=spreadsheet_id,
                    addParents=folder_id,
                    fields='id, parents'
                ).execute()
                print(f"✅ Moved to folder successfully!")
                
            except Exception as e:
                print(f"⚠️  Could not move to folder: {e}")
        
        # Clean up
        print("\nCleaning up...")
        drive_service.files().delete(fileId=spreadsheet_id).execute()
        print("✅ Test file deleted")
        
        print("\n🎉 SOLUTION FOUND!")
        print("We can create via Sheets API and then move to folder!")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Check for workspace/domain restrictions
    print("\n\n🏢 WORKSPACE/DOMAIN CHECK")
    print("-"*70)
    
    try:
        about = drive_service.about().get(
            fields='user,storageQuota,canCreateDrives,canCreateTeamDrives'
        ).execute()
        
        user = about.get('user', {})
        print(f"User email: {user.get('emailAddress')}")
        print(f"Permission ID: {user.get('permissionId')}")
        print(f"Can create shared drives: {about.get('canCreateDrives', 'Unknown')}")
        
    except Exception as e:
        print(f"Could not get workspace info: {e}")
    
    # Check project quotas
    print("\n\n⚙️  PROJECT SETTINGS")
    print("-"*70)
    print(f"Project: {creds_data.get('project_id')}")
    print(f"\nTo check API quotas:")
    print(f"https://console.cloud.google.com/apis/api/sheets.googleapis.com/quotas?project={creds_data.get('project_id')}")
    print(f"https://console.cloud.google.com/apis/api/drive.googleapis.com/quotas?project={creds_data.get('project_id')}")
    
    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        final_diagnostic()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()