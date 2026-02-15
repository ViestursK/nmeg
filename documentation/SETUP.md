# Setup Guide

Complete setup from scratch. Everything you need.

---

## Part 1: Prerequisites (15-20 minutes)

### 1. Install Docker Desktop

**Download:** https://www.docker.com/products/docker-desktop/

- Windows: Choose your version (most likely Intel/AMD)
- Mac: Choose Apple Silicon or Intel based on your Mac
- Install, start it, wait for "Docker Desktop is running"

---

### 2. Google Cloud Setup

#### Create Service Account & Get Credentials

1. Go to https://console.cloud.google.com
2. Create new project (or select existing)
3. Search "APIs & Services" → Enable these APIs:
   - Google Sheets API
   - Google Drive API
4. Go to "Credentials" → "Create Credentials" → "Service Account"
5. Name it (e.g., "trustpilot-reporter"), click "Create"
6. Skip role assignment, click "Continue" → "Done"
7. Click the service account email you just created
8. Go to "Keys" tab → "Add Key" → "Create New Key" → "JSON"
9. Download saves as `project-name-xxxxx.json`
10. **Copy the service account email** (looks like: `name@project.iam.gserviceaccount.com`)

#### Rename & Move File

- Rename downloaded JSON to: `service_account.json`
- Move it to: `trustpilot-analytics/sheets/service_account.json`

---

### 3. Google Sheet Setup

#### Create Sheet

1. Go to https://drive.google.com
2. New → Google Sheets → Blank spreadsheet
3. Name it: **Trustpilot Report** (exact name matters)
4. Copy the **Folder ID** from URL:
   - URL: `https://drive.google.com/drive/folders/1ABC123xyz`
   - Folder ID: `1ABC123xyz`

#### Share with Service Account

1. Click "Share" button
2. Paste the service account email you copied earlier
3. Give it "Editor" access
4. Uncheck "Notify people"
5. Click "Share"

---

### 4. Extract Trustpilot JWT Token

#### Steps:

1. Login to https://www.trustpilot.com/review/ketogo.app? with your account
2. Press **F12** to open Developer Tools
3. Go to **Network** tab (Chrome) → Refresh the page → under filter select **All** → open **ketogo.app**
4. Left Request Headers → sidebar → Cookie
5. Find cookie named: **jwt**
6. Copy the entire **Value** column (starts with `eyJ...`, usually 300-400 characters)

**Important:** 
- Don't include `jwt=` prefix
- Don't include semicolon at end
- Just the token itself: `eyJhbGc...xyz`

**Token expires in ~90 days** - you'll need to repeat this step when it expires.

---

## Part 2: Configuration (5 minutes)

### 1. Create .env File

**Mac:**
```bash
cd ~/path/to/trustpilot-analytics
cp .env.example .env
nano .env
```

**Windows:**
```powershell
cd D:\path\to\trustpilot-analytics
copy .env.example .env
notepad .env
```

### 2. Fill in Values

Replace these in `.env`:
```bash
# Database password - choose any secure password
DB_PASS=your_secure_password_here

# JWT token you copied from Trustpilot
TRUSTPILOT_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx.yyyyy

# Google Drive folder ID you copied
GOOGLE_DRIVE_FOLDER_ID=1ABC123xyz

# Leave these as-is:
GOOGLE_SHEETS_CREDENTIALS=sheets/service_account.json
MASTER_SPREADSHEET_NAME=Trustpilot Report
```

**Save and close.**

---

### 3. Configure Brands (Optional)

Edit `brands_config.json` if you want different brands:
```json
{
  "brands": [
    {
      "domain": "yourbrand.com",
      "name": "Your Brand Name"
    },
    {
      "domain": "yourotherbrand.com",
      "name": "Your Other Brand Name"
    }
  ]
}
```

- `domain`: Trustpilot domain (from URL: trustpilot.com/review/**yourbrand.com**)
- `name`: Display name in Google Sheets

---

## Part 3: Installation & First Run

### Mac/Linux (Terminal)
```bash
# Navigate to project
cd ~/path/to/trustpilot-analytics

# Build (takes 2-5 min first time)
docker-compose build

# Start containers
docker-compose up -d

# Wait for database to start
sleep 10

# Initialize database
docker-compose exec app python setup_db.py

# Verify setup
docker-compose exec app python preflight_check.py

# Full backfill (30-60 min depending on reviews)
docker-compose exec app python weekly_job.py --backfill
```

---

### Windows (PowerShell/CMD)
```powershell
# Navigate to project
cd D:\path\to\trustpilot-analytics

# Build (takes 2-5 min first time)
docker-compose build

# Start containers
docker-compose up -d

# Wait for database to start
timeout /t 10

# Initialize database
docker-compose exec app python setup_db.py

# Verify setup
docker-compose exec app python preflight_check.py

# Full backfill (30-60 min depending on reviews)
docker-compose exec app python weekly_job.py --backfill
```

---

## Part 4: Verify It Worked

### 1. Check Logs

Look for:
```
✅ Fetched: X,XXX reviews
✅ Saved: X,XXX new reviews
✅ Uploaded: XX weeks
```

If you see errors, check `Troubleshooting.md`

### 2. Check Google Sheet

Open your "Trustpilot Report" sheet:
- Should have `raw_data` tab
- Should have rows of weekly data
- Each row = one brand + one week

---

## Daily Usage
```bash
# Start system
docker-compose up -d

# Stop system
docker-compose down

# View logs
docker-compose logs -f app

# Run weekly update manually
docker-compose exec app python weekly_job.py

# Test specific week
docker-compose exec app python weekly_job.py --week 2026-W06
```

---

## Maintenance

### JWT Token Expires (every ~90 days)

When you see "Token expired" errors:

1. Extract new JWT token (see Part 1, Step 4)
2. Update `.env` file with new token
3. Restart: `docker-compose restart app`

### Add/Remove Brands

1. Edit `brands_config.json`
2. Restart: `docker-compose restart app`
3. Run backfill for new brands: `docker-compose exec app python weekly_job.py --backfill`

### Update Credentials

After changing `.env`, `service_account.json`, or `brands_config.json`:
```bash
docker-compose restart app
```

No rebuild needed.

---

## Troubleshooting

See `Troubleshooting.md` for common issues.

Quick checks:
```bash
# Check if containers running
docker-compose ps

# Check logs for errors
docker-compose logs app

# Validate environment
docker-compose exec app python preflight_check.py
```

---

## Files You Need

After setup, verify you have:
```
trustpilot-analytics/
├── .env                           ✅ Created from .env.example
├── sheets/service_account.json    ✅ Downloaded from Google Cloud
└── brands_config.json             ✅ Edited with your brands
```