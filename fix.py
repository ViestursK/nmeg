#!/usr/bin/env python3
"""
Expand Master Index and Add Helper Column
Fixes the column limit issue
"""

import os
import sys
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

load_dotenv()


def expand_and_add_helper():
    """Expand Master Index columns and add lookup helper"""
    
    print("\n" + "="*70)
    print("EXPANDING MASTER INDEX & ADDING HELPER COLUMN")
    print("="*70 + "\n")
    
    # Setup credentials
    spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Report")
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    
    if not creds_path or not os.path.exists(creds_path):
        print("❌ Credentials not found")
        sys.exit(1)
    
    scopes = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    print("✅ Authenticated\n")
    
    # Find spreadsheet
    print(f"🔍 Looking for: '{spreadsheet_name}'")
    workbook = gc.open(spreadsheet_name)
    spreadsheet_id = workbook.id
    print(f"✅ Found: {workbook.title}\n")
    
    # Get Master Index sheet metadata
    sheet_metadata = sheets_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()
    
    master_index_sheet_id = None
    current_cols = 0
    
    for sheet in sheet_metadata['sheets']:
        if sheet['properties']['title'] == 'Master Index':
            master_index_sheet_id = sheet['properties']['sheetId']
            current_cols = sheet['properties']['gridProperties']['columnCount']
            print(f"📊 Master Index: {current_cols} columns currently")
            break
    
    if not master_index_sheet_id:
        print("❌ Master Index not found")
        sys.exit(1)
    
    # Expand to 30 columns if needed
    if current_cols < 30:
        print(f"\n🔧 Expanding from {current_cols} to 30 columns...")
        
        expand_request = {
            'updateSheetProperties': {
                'properties': {
                    'sheetId': master_index_sheet_id,
                    'gridProperties': {
                        'columnCount': 30
                    }
                },
                'fields': 'gridProperties.columnCount'
            }
        }
        
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [expand_request]}
        ).execute()
        
        print("   ✅ Expanded to 30 columns")
    else:
        print(f"   ✅ Already has {current_cols} columns")
    
    # Now add helper column
    print("\n📝 Adding helper column U (lookup_key)...")
    
    master_index = workbook.worksheet('Master Index')
    
    # Add header
    master_index.update(values=[['lookup_key']], range_name='U1')
    
    # Get number of data rows
    values = master_index.get_all_values()
    last_row = len(values)
    
    print(f"   Found {last_row} rows (including header)")
    
    if last_row > 1:
        # Add formula to U2
        master_index.update(values=[['=A2&"|"&B2']], range_name='U2')
        
        # Copy down to all rows
        if last_row > 2:
            formulas = [[f'=A{i}&"|"&B{i}'] for i in range(2, last_row + 1)]
            master_index.update(values=formulas, range_name=f'U2:U{last_row}')
        
        print(f"   ✅ Helper formulas added (U2:U{last_row})")
    
    print("\n" + "="*70)
    print("✅ MASTER INDEX EXPANDED!")
    print("="*70)
    print(f"\n🔗 Open: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print("\nNext steps:")
    print("  1. Dashboard formulas should now work!")
    print("  2. Select brand in B3")
    print("  3. Select week in B4")
    print("  4. KPIs should populate")
    print("\nDon't forget to update B4 data validation:")
    print("  • Click B4 → Data → Data validation")
    print("  • Change range to: Dashboard!Z2:Z\n")


if __name__ == "__main__":
    try:
        expand_and_add_helper()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)