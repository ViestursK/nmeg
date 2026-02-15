# Trustpilot Analytics

Automated Trustpilot review scraper + Google Sheets reporter.

## Quick Start

```bash
# Install Docker Desktop first
./setup_mac.sh
```

See `SETUP.md` for details.

---

## Daily Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f app

# Status
docker-compose ps

# Run job manually
docker-compose exec app python weekly_job.py

# Test specific week
docker-compose exec app python weekly_job.py --week 2026-W06

# Backfill historical data
docker-compose exec app python weekly_job.py --backfill

# Validate setup
docker-compose exec app python preflight_check.py

# Test JWT token
docker-compose exec app python tests/test_jwt.py
```

---

## Updating

### Changed .env or credentials?
```bash
docker-compose restart app
```

### Changed code?
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Files You Need

```
trustpilot-analytics/
├── .env                              ← Create from .env.template
├── sheets/service_account.json       ← Download from Google Cloud
└── brands_config.json               ← Edit with your brands
```

Everything else is provided.

---

## Maintenance

**Every 90 days:** Renew JWT token
1. Extract from browser (F12 → Cookies → jwt)
2. Update `.env`
3. `docker-compose restart app`

**As needed:** Add/remove brands in `brands_config.json`, restart app

---

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues.

Quick fixes:
- Restart: `docker-compose restart`
- Rebuild: `docker-compose build && docker-compose up -d`
- Reset: `docker-compose down -v && docker-compose up -d`
- Logs: `docker-compose logs app`