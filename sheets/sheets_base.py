#!/usr/bin/env python3
"""
Base Google Sheets handler with shared connection logic
"""

import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

load_dotenv()

class SheetsBase:
    """Shared Google Sheets connection and utilities"""
    
    def __init__(self):
        self.spreadsheet_name = os.getenv("MASTER_SPREADSHEET_NAME", "Trustpilot Report")
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        
        if not self.folder_id or not creds_path:
            raise ValueError("Missing GOOGLE_DRIVE_FOLDER_ID or GOOGLE_SHEETS_CREDENTIALS in .env")
        
        # Handle relative paths
        if not os.path.isabs(creds_path):
            # Get project root (parent of sheets directory)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # If we're IN the sheets directory, go up one level
            if os.path.basename(current_dir) == 'sheets':
                project_root = os.path.dirname(current_dir)
            else:
                project_root = current_dir
            
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
        # Setup credentials
        self.scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        self.creds = Credentials.from_service_account_file(creds_path, scopes=self.scopes)
        self.gc = gspread.authorize(self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)
        
        print("✅ Authenticated with Google API")
    
    def find_master_sheet(self):
        """Find master spreadsheet ID"""
        query = (
            f"'{self.folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.spreadsheet' and "
            f"name='{self.spreadsheet_name}' and "
            f"trashed=false"
        )
        
        results = self.drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            raise FileNotFoundError(
                f"❌ Master sheet '{self.spreadsheet_name}' not found in folder.\n"
                f"   Create it at: https://drive.google.com/drive/folders/{self.folder_id}"
            )
        
        return files[0]['id']
    
    def get_workbook(self):
        """Get workbook object"""
        spreadsheet_id = self.find_master_sheet()
        return self.gc.open_by_key(spreadsheet_id), spreadsheet_id
    
    def get_or_create_tab(self, workbook, tab_name):
        """Get or create worksheet tab"""
        try:
            return workbook.worksheet(tab_name)
        except:
            print(f"  ➕ Creating tab: {tab_name}")
            return workbook.add_worksheet(title=tab_name, rows=5000, cols=50)