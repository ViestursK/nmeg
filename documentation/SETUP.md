# Mac Setup Guide - Simplified

Complete setup tested and verified. Takes ~60 minutes total.

---

## Prerequisites (15 min)

### 1. Install Docker Desktop

**Download:** https://www.docker.com/products/docker-desktop/

- Choose **Apple Silicon** (M1/M2/M3) or **Intel** 
  - Check: Apple menu → About This Mac
- Install and **start** Docker Desktop
- Wait for green "Docker Desktop is running" in menu bar

---

### 2. Get Google Credentials

#### Create Service Account:
1. https://console.cloud.google.com
2. New Project → name: `trustpilot-analytics`
3. Enable APIs:
   - Search: "Google Sheets API" → Enable
   - Search: "Google Drive API" → Enable
4. Credentials → Create Credentials → Service Account
5. Name: `trustpilot-reporter` → Create → Skip roles → Done
6. **COPY the email** (ends with `.iam.gserviceaccount.com`)
7. Keys tab → Add Key → Create New Key → JSON
8. Rename downloaded file to: `service_account.json`

#### Move File:
```bash
cd ~/Desktop/trustpilot-analytics
mkdir -p sheets
mv ~/Downloads/*trustpilot*.json sheets/service_account.json
```

---

### 3. Copy Template Sheet

**IMPORTANT: Use the pre-built template with dashboard!**

1. **Get the template link** (ask for the Google Sheet link)
2. Open the template → **File** → **Make a copy**
3. Google will name it "Copy of Trustpilot Report"
4. **Rename it to exactly:** `Trustpilot Report` (remove "Copy of")
5. **Move it to a folder** (not in root "My Drive")
6. **Verify the sheet has 3 tabs:**
   - `dashboard` (pre-built charts/KPIs)
   - `helpers` (formulas)
   - `raw_data` (Python writes here - will be empty initially)

**Share with Service Account:**
1. Click **Share** button
2. Paste service account email → **Editor** → Uncheck notify → Share
3. Also share the **folder** it's in with service account (Editor)

**Get Folder ID:**
1. Navigate to the folder containing your sheet
2. Copy ID from URL: `https://drive.google.com/drive/folders/1ABC123xyz`
3. ID is: `1ABC123xyz` ⚠️ **No trailing dash or extra characters!**

---

### 4. Get Trustpilot JWT Token

1. Browser: https://www.trustpilot.com/review/ketogo.app
2. Login if needed
3. `Cmd + Option + I` → **Application** tab
4. Sidebar: **Cookies** → `https://www.trustpilot.com`
5. Find: `jwt` cookie
6. Copy **Value** only (~300-400 chars starting with `eyJ`)

---

## Setup (10 min)

### 1. Configure Environment

```bash
cd ~/Desktop/trustpilot-analytics

# Create .env from template
cp .env.example .env

# Edit it
nano .env
# or
open -e .env
```

**Fill in these values:**

```bash
# Change password to something secure
DB_PASS=your_secure_password_here

# Paste JWT token (no quotes)
TRUSTPILOT_JWT=eyJhbGci...your_token_here

# Paste folder ID (NO TRAILING DASH!)
GOOGLE_DRIVE_FOLDER_ID=1ABC123xyz

# Keep these as-is:
DB_HOST=postgres
DB_PORT=5432
DB_NAME=trustpilot_analytics
DB_USER=postgres
GOOGLE_SHEETS_CREDENTIALS=sheets/service_account.json
MASTER_SPREADSHEET_NAME=Trustpilot Report
```

Save (`Cmd + S`) and close.

---

### 2. Verify Files Exist

```bash
ls -la .env
ls -la sheets/service_account.json
ls -la brands_config.json
```

All three should show file sizes.

---

## Installation (5 min)

```bash
# Build containers (2-5 min)
docker-compose build

# Start
docker-compose up -d

# Wait for database
sleep 15

# Initialize database (use -m flag!)
docker-compose exec app python -m db.setup
```

When prompted, type: `yes`

---

## Validation (2 min)

```bash
# Check setup
docker-compose exec app python preflight_check.py
```

**All checks should pass except:**
- ✅ Ignore ".env file not found" in Docker - this is normal

**Verify environment variables:**
```bash
docker-compose exec app printenv | grep GOOGLE_DRIVE_FOLDER_ID
```

Should show your folder ID **with no trailing dash**.

---

## First Run - Backfill (30-60 min)

```bash
# Start backfill
docker-compose exec app python weekly_job.py --backfill
```

**This will:**
- Scrape all reviews from Trustpilot
- Store in database
- Generate weekly reports
- Upload to Google Sheets

**Leave it running.** Check progress every 10 minutes.

---

## Verify Success

### 1. Check Completion
```bash
docker-compose logs app | tail -20
```

Should see: `✅ BACKFILL COMPLETE`

### 2. Check Google Sheets
- Open "Trustpilot Report" sheet
- Should have 3 tabs: `dashboard`, `helpers`, `raw_data`
- `raw_data` tab should have many rows of weekly data
- `dashboard` tab should show charts and KPIs (may need refresh)

### 3. Check Cron
```bash
docker-compose exec app crontab -l
```

Should show: `0 0 * * 1 /app/run_weekly_job.sh...`

---

## Daily Usage

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f app

# Manual run
docker-compose exec app python weekly_job.py

# Check cron log
docker-compose exec app cat /var/log/trustpilot-cron.log
```

---

## Automation

**The system auto-runs every Monday at midnight via cron.**

Nothing else needed! It will:
1. Scrape last 30 days
2. Generate report for completed week
3. Upload to Google Sheets

---

## Troubleshooting

**Container won't start:**
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

**"File not found" error with Google Drive:**
- Check folder ID has **no trailing dash**
- Verify sheet is in that folder
- Must restart after changing .env: `docker-compose restart app`
- **Sheet must be named exactly "Trustpilot Report"** (not "Copy of...")
- Sheet must have `raw_data` tab (from template)

**Dashboard not showing data:**
- Make sure you copied the template (has dashboard, helpers, raw_data tabs)
- Check `raw_data` tab has data
- Dashboard may need manual refresh in Google Sheets

**Database empty / "Company not found":**
- Run backfill first: `docker-compose exec app python weekly_job.py --backfill`

**"Module not found" errors:**
- Use `-m` flag: `python -m db.setup` not `python db/setup.py`

**Cron not working:**
- Check it exists: `docker-compose exec app crontab -l`
- Check process file: `docker-compose exec app ls -la /var/run/crond.pid`
- Manual test: `docker-compose exec app /app/run_weekly_job.sh`

---

## Maintenance

**Every ~90 days:**
- JWT token expires
- Extract new token (see step 4 in Prerequisites)
- Update `.env`
- Restart: `docker-compose restart app`

**Add/Remove Brands:**
- Edit `brands_config.json`
- Restart: `docker-compose restart app`
- Backfill new brands: `docker-compose exec app python weekly_job.py --backfill`

---

## Common Pitfalls

❌ **Creating blank sheet instead of copying template** → Dashboard won't work!
❌ **Not renaming "Copy of Trustpilot Report"** → System can't find it
❌ **Folder ID with trailing dash** → Remove the dash!
❌ **Not sharing folder with service account** → Permission errors
❌ **Using `python db/setup.py`** → Use `python -m db.setup`
❌ **Not restarting after .env change** → Always: `docker-compose restart app`
❌ **Testing with --week before backfill** → Database is empty, run backfill first
❌ **Forgetting to share sheet with service account** → No permissions = errors

---

**Done! System is fully automated.** 🎉