# Pre-Setup Checklist ✅

**Complete this checklist BEFORE running setup_mac.sh**

Print this page and check off each item as you complete it.

---

## Part 1: Google Sheet Template

- [ ] Opened template link: https://docs.google.com/spreadsheets/d/1ZI85ZEa_TbEBonQNZaeE3XM5WwF7Fhvq2TfHk9aFwt4/edit?usp=share_link
- [ ] Clicked **File** → **Make a copy**
- [ ] Renamed to exactly: **Trustpilot Report** (removed "Copy of")
- [ ] Verified 3 tabs exist: `dashboard`, `helpers`, `raw_data`
- [ ] Moved sheet to a folder (not in "My Drive" root)

**Folder URL:** _______________________________________
**Folder ID:** ________________________________________
*(Copy from URL after /folders/, NO trailing dash!)*

---

## Part 2: Google Service Account

- [ ] Created Google Cloud project
- [ ] Enabled Google Sheets API
- [ ] Enabled Google Drive API
- [ ] Created service account named: `trustpilot-reporter`
- [ ] Downloaded JSON credentials file
- [ ] Renamed file to: `service_account.json`
- [ ] Moved to: `trustpilot-analytics/sheets/service_account.json`

**Service Account Email:** ___________________________________
*(Looks like: name@project.iam.gserviceaccount.com)*

---

## Part 3: Sharing & Permissions

- [ ] Shared **the sheet** with service account email (Editor)
- [ ] Shared **the folder** with service account email (Editor)
- [ ] Unchecked "Notify people" when sharing
- [ ] Verified service account appears in "Share" dialog

---

## Part 4: Trustpilot Token

- [ ] Logged into Trustpilot.com
- [ ] Opened DevTools (Cmd + Option + I)
- [ ] Found JWT cookie in Application → Cookies
- [ ] Copied token value (starts with `eyJ`, ~300-400 chars)
- [ ] Did NOT include cookie name or semicolon

**Token (first 20 chars):** ___________________________
*(Just for verification - don't write full token here!)*

---

## Part 5: Docker Desktop

- [ ] Downloaded Docker Desktop for Mac
- [ ] Chose correct version (Apple Silicon or Intel)
- [ ] Installed Docker Desktop
- [ ] Started Docker Desktop
- [ ] See green "Docker Desktop is running" in menu bar

---

## Part 6: Environment File

- [ ] Opened `trustpilot-analytics/.env` in text editor
- [ ] Set `DB_PASS` to a secure password
- [ ] Set `GOOGLE_DRIVE_FOLDER_ID` (NO trailing dash!)
- [ ] Set `TRUSTPILOT_JWT` (the token without "jwt="prefix and semi-column (;) at the end.)
- [ ] Verified `MASTER_SPREADSHEET_NAME=Trustpilot Report`
- [ ] Saved file

---

## Part 7: Brands Configuration

- [ ] Edited `brands_config.json` if needed
- [ ] All brand domains are correct (from Trustpilot URLs)
- [ ] Brand display names are set

---

## Final Verification

Before running setup:

```bash
cd ~/Desktop/trustpilot-analytics

# All these should exist:
ls -la .env
ls -la sheets/service_account.json
ls -la brands_config.json

# Check .env has no CHANGE_ME placeholders:
grep CHANGE_ME .env
# ^ Should return nothing!

# Verify Docker is running:
docker info
```

**Next Step:** Run `./setup_mac.sh` and follow prompts!