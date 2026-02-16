#!/bin/bash
# Quick Setup Script for Mac
# Run this after installing Docker Desktop

set -e  # Exit on error

echo "========================================================================"
echo "TRUSTPILOT ANALYTICS - DOCKER SETUP"
echo "========================================================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found!"
    echo ""
    echo "Please install Docker Desktop first:"
    echo "  1. Go to: https://www.docker.com/products/docker-desktop/"
    echo "  2. Download for Mac (Apple Silicon or Intel)"
    echo "  3. Install and start Docker Desktop"
    echo "  4. Run this script again"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is installed and running"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo ""
    echo "Creating template .env file..."
    cat > .env << 'EOF'
# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=trustpilot_analytics
DB_USER=postgres
DB_PASS=CHANGE_ME_secure_password

# Google Sheets
GOOGLE_DRIVE_FOLDER_ID=CHANGE_ME_your_folder_id
GOOGLE_SHEETS_CREDENTIALS=sheets/service_account.json
MASTER_SPREADSHEET_NAME=Trustpilot Report

# Trustpilot
TRUSTPILOT_JWT=CHANGE_ME_your.jwt.token
EOF
    echo "✅ Created .env template"
    echo ""
    echo "⚠️  IMPORTANT: Before running this script, you need to:"
    echo ""
    echo "1. Copy the Google Sheet template:"
    echo "   https://docs.google.com/spreadsheets/d/1ZI85ZEa_TbEBonQNZaeE3XM5WwF7Fhvq2TfHk9aFwt4/edit?usp=share_link"
    echo "   → File → Make a copy"
    echo "   → Rename to: Trustpilot Report"
    echo ""
    echo "2. Share it AND the folder with your service account (Editor)"
    echo ""
    echo "3. Get the folder ID from the URL (no trailing dash!)"
    echo ""
    echo "4. Extract JWT token from Trustpilot browser cookies"
    echo ""
    echo "Then edit .env and add:"
    echo "  - DB_PASS (secure password)"
    echo "  - GOOGLE_DRIVE_FOLDER_ID (from folder URL, no trailing dash!)"
    echo "  - TRUSTPILOT_JWT (from browser cookies)"
    echo ""
    echo "   Run: nano .env"
    echo ""
    read -p "Press Enter after completing ALL steps above..."
fi

# Verify .env has been updated
if grep -q "CHANGE_ME" .env; then
    echo "❌ .env file still contains CHANGE_ME placeholders"
    echo ""
    echo "Please edit .env and replace all CHANGE_ME values with actual credentials"
    echo "Run: nano .env"
    exit 1
fi

# Check for credentials file
if [ ! -f sheets/service_account.json ]; then
    echo "⚠️  Google credentials not found"
    echo ""
    echo "Please copy your service_account.json file to:"
    echo "   sheets/service_account.json"
    echo ""
    read -p "Press Enter after copying the file..."
fi

if [ ! -f sheets/service_account.json ]; then
    echo "❌ Still can't find service_account.json"
    echo "Setup cannot continue without credentials."
    exit 1
fi

echo ""
echo "========================================================================"
echo "BUILDING DOCKER CONTAINERS"
echo "========================================================================"
echo ""
echo "This will take 2-5 minutes on first run..."
echo ""

docker-compose build

echo ""
echo "========================================================================"
echo "STARTING CONTAINERS"
echo "========================================================================"
echo ""

docker-compose up -d

echo ""
echo "Waiting for database to be ready..."
sleep 15

echo ""
echo "========================================================================"
echo "INITIALIZING DATABASE"
echo "========================================================================"
echo ""

docker-compose exec app python -m db.setup

echo ""
echo "========================================================================"
echo "RUNNING PREFLIGHT CHECK"
echo "========================================================================"
echo ""

docker-compose exec app python preflight_check.py

echo ""
echo "========================================================================"
echo "✅ SETUP COMPLETE!"
echo "========================================================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Test (should show 'no data' - that's expected):"
echo "   docker-compose exec app python weekly_job.py --week 2026-W06"
echo ""
echo "2. Backfill historical data (30-60 min):"
echo "   docker-compose exec app python weekly_job.py --backfill"
echo ""
echo "3. Verify automatic scheduling:"
echo "   docker-compose exec app crontab -l"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 AUTOMATION STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ System is RUNNING - Cron will trigger every Monday at midnight"
echo ""
echo "⚠️  Containers must stay running for automation to work!"
echo ""
echo "Daily commands:"
echo "  • View logs:    docker-compose logs -f app"
echo "  • Check status: docker-compose ps"
echo "  • Manual run:   docker-compose exec app python weekly_job.py"
echo ""
echo "Maintenance:"
echo "  • Restart:      docker-compose restart app"
echo "  • Stop system:  docker-compose down    (⚠️ disables automation!)"
echo "  • Start again:  docker-compose up -d"
echo ""