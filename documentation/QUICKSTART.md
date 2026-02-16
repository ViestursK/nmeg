# 🚀 Quick Setup - Mac

**Total Time: ~60 minutes**

---

## 📋 Before You Start

### 1. Template Sheet (Required!)
**Link:** https://docs.google.com/spreadsheets/d/1ZI85ZEa_TbEBonQNZaeE3XM5WwF7Fhvq2TfHk9aFwt4/edit?usp=share_link

- Click link → File → Make a copy
- Rename to: **Trustpilot Report**
- Move to a folder (not root "My Drive")
- Verify 3 tabs: `dashboard`, `helpers`, `raw_data`

### 2. Google Service Account
- Create at: https://console.cloud.google.com
- Enable: Google Sheets API + Google Drive API
- Download JSON credentials → rename to `service_account.json`
- Copy service account email (ends with `.iam.gserviceaccount.com`)

### 3. Share Sheet & Folder
- Share sheet with service account (Editor)
- Share folder with service account (Editor)
- Get folder ID from URL (⚠️ NO trailing dash!)

### 4. Trustpilot JWT Token
- Login: https://www.trustpilot.com
- DevTools (Cmd+Option+I) → Application → Cookies
- Copy `jwt` cookie value (~300-400 chars)

---

## ⚙️ Setup

```bash
cd ~/Desktop/trustpilot-analytics

# 1. Configure
cp .env.example .env
nano .env  # Fill in: DB_PASS, GOOGLE_DRIVE_FOLDER_ID, TRUSTPILOT_JWT

# 2. Run setup
chmod +x setup_mac.sh
./setup_mac.sh

# 3. Backfill data (30-60 min)
docker-compose exec app python weekly_job.py --backfill
```

---

## ✅ Daily Use

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f app

# Manual run
docker-compose exec app python weekly_job.py
```

**⚠️ Keep containers running for automatic Monday updates!**

---

## 🆘 Troubleshooting

**"File not found" error:**
- Check folder ID has no trailing dash
- Verify sheet name is exactly "Trustpilot Report"

**"Company not found" error:**
- Run backfill first: `docker-compose exec app python weekly_job.py --backfill`

**Full guide:** See `SETUP.md`

---

**Template:** https://docs.google.com/spreadsheets/d/1ZI85ZEa_TbEBonQNZaeE3XM5WwF7Fhvq2TfHk9aFwt4/edit?usp=share_link