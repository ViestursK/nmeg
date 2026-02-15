# Setup Guide

## Prerequisites (30 min)

### 1. Google Cloud Service Account
1. Create project at https://console.cloud.google.com
2. Enable: Google Sheets API + Google Drive API
3. Create service account → Download JSON key
4. Save as `sheets/service_account.json`
5. Copy service account email (need it for step 2)

### 2. Google Sheet
1. Create sheet named "Trustpilot Report"
2. Share with service account email as Editor
3. Get folder ID from Drive URL (optional)

### 3. Trustpilot JWT
1. Login to trustpilot.com as a normal user (SSO with gmail)
2. F12 → Network → *Refresh the page* → "Ketogo.app?" → Request Headers → Cookie → look for: jwt=xxxx.yyyy.zzzz
3. Copy entire value (starts with eyJ...) in your .env to TRUSTPILOT_JWT=

### 4. Docker Desktop
Download from docker.com, install, start it.

---

## Installation (5 min)

### 1. Create .env file
```bash
cp .env.template .env
nano .env
```

Fill in:
```bash
DB_PASS=any_password_you_want
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_or_blank
TRUSTPILOT_JWT=eyJ_your_token_here
```

### 2. Add credentials
Place service_account.json in `sheets/service_account.json`

### 3. Edit brands
Edit `brands_config.json` with your brands:
```json
{
  "brands": [
    {"domain": "yourbrand.com", "name": "Your Brand"},
    {"domain": "yourotherbrand.com", "name": "Your Other Brand"}
  ]
}
```

### 4. Run setup
```bash
chmod +x setup_mac.sh
./setup_mac.sh
```

Done. System is running.

---

## Test (2 min)

```bash
# Verify
docker-compose exec app python preflight_check.py

# Test one week
docker-compose exec app python weekly_job.py --week 2026-W06

# Backfill all data (30+ min)
docker-compose exec app python weekly_job.py --backfill
```

---

## Weekly Automation

Add to crontab:
```bash
crontab -e
# Add:
0 0 * * 1 cd ~/trustpilot-analytics && docker-compose exec -T app python weekly_job.py
```

Runs every Monday at midnight.

---

## Maintenance

### JWT expires every 90 days:
1. Extract new token (step 3 above)
2. Update `.env`
3. `docker-compose restart app`

### Add/remove brands:
1. Edit `brands_config.json`
2. `docker-compose restart app`

---

## Important

**Changing credentials (.env, service_account.json, brands_config.json)?**
→ Just restart: `docker-compose restart app`

**NO REBUILD NEEDED**

**Changing Python code?**
→ Rebuild: `docker-compose down && docker-compose build && docker-compose up -d`