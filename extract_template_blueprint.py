from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import json
import os

TEMPLATE_NAME = "sample template"
CREDS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "sheets/service_account.json")

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

def find_spreadsheet_id(drive):
    query = (
        f"name = '{TEMPLATE_NAME}' and "
        "mimeType = 'application/vnd.google-apps.spreadsheet' and "
        "trashed = false"
    )

    res = drive.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        supportsAllDrives=True,
    ).execute()

    files = res.get("files", [])
    if not files:
        raise FileNotFoundError(
            f"❌ No spreadsheet found with name: {TEMPLATE_NAME}"
        )

    if len(files) > 1:
        print("⚠️ Multiple files found, using the first one:")
        for f in files:
            print(" -", f["name"], f["id"])

    return files[0]["id"]

def extract_template_blueprint(output_file="style_blueprint.json"):
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)

    spreadsheet_id = find_spreadsheet_id(drive)
    print("✅ Found spreadsheet ID:", spreadsheet_id)

    spreadsheet = sheets.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        includeGridData=True
    ).execute()

    blueprint = {
        "spreadsheet_title": spreadsheet["properties"]["title"],
        "spreadsheet_id": spreadsheet_id,
        "sheets": {}
    }

    for sheet in spreadsheet["sheets"]:
        title = sheet["properties"]["title"]
        grid_props = sheet["properties"]["gridProperties"]
        data = sheet["data"][0]

        sheet_bp = {
            "frozen_rows": grid_props.get("frozenRowCount", 0),
            "frozen_cols": grid_props.get("frozenColumnCount", 0),
            "column_widths": [],
            "row_heights": [],
            "cells": [],
            "merges": sheet.get("merges", []),
        }

        for col in data.get("columnMetadata", []):
            sheet_bp["column_widths"].append(col.get("pixelSize"))

        for row in data.get("rowMetadata", []):
            sheet_bp["row_heights"].append(row.get("pixelSize"))

        # Limit formatting capture to top area (keeps JSON sane)
        for r, row in enumerate(data.get("rowData", [])[:20]):
            for c, cell in enumerate(row.get("values", [])):
                fmt = cell.get("effectiveFormat")
                if fmt:
                    sheet_bp["cells"].append({
                        "row": r,
                        "col": c,
                        "format": fmt
                    })

        blueprint["sheets"][title] = sheet_bp

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(blueprint, f, indent=2)

    print(f"🎨 Template blueprint saved → {output_file}")

if __name__ == "__main__":
    extract_template_blueprint()
