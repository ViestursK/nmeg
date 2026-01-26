import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from gspread_dataframe import set_with_dataframe
import pandas as pd

# --- LOAD .env ---
load_dotenv()

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# --- AUTHENTICATION ---
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# --- STEP 1: Look for the spreadsheet by name in the folder ---
query = f"'{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and name='{SPREADSHEET_NAME}'"
results = drive_service.files().list(
    q=query,
    spaces='drive',
    fields='files(id, name)',
    supportsAllDrives=True
).execute()

files = results.get('files', [])

if files:
    # Found existing spreadsheet
    spreadsheet_id = files[0]['id']
    print(f"Found existing spreadsheet: {SPREADSHEET_NAME} (ID: {spreadsheet_id})")
else:
    # inform
    print(f"Spreadsheet {SPREADSHEET_NAME} not found in folder {FOLDER_ID}.")
    print("Please create the spreadsheet manually and rerun the script.")
    exit(1)

# --- STEP 2: Open with gspread ---
workbook = client.open_by_key(spreadsheet_id)

# --- STEP 3: OPTIONAL: write sample DataFrame ---
df = pd.DataFrame({
    'Name': ['Alice', 'Bob', 'Charlie'],
    'Score': [95, 88, 92]
})
worksheet = workbook.sheet1
set_with_dataframe(worksheet, df)
print("Sample DataFrame written successfully!")
