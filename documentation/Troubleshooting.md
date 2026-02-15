# Troubleshooting

## Docker Issues

### "Docker not found"
- Install Docker Desktop
- Make sure it's running (check menu bar icon)

### "Cannot connect to daemon"
- Docker Desktop not running → Start it
- Restart Docker Desktop

### "Port already in use"
Change port in `.env`:
```bash
DB_PORT=5433
```

---

## Database Issues

### "Connection refused"
```bash
# Wait 30 seconds for DB to start
docker-compose restart postgres
```

### "Database does not exist"
```bash
docker-compose exec app python db/setup.py
```

### Reset database (WARNING: deletes all data)
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec app python db/setup.py
```

---

## Google Sheets Issues

### "Permission denied"
- Verify service account email is added to sheet as Editor
- Wait 1 minute for permissions to propagate
- Check sheet name in `.env` matches exactly (case-sensitive)

### "Credentials not found"
```bash
# Verify file exists
ls sheets/service_account.json

# Check it's valid JSON
cat sheets/service_account.json | python -m json.tool
```

---

## Scraping Issues

### "No reviews found"
```bash
# Test JWT token
docker-compose exec app python tests/test_jwt.py

# If expired, extract new one and update .env
docker-compose restart app
```

### "Limited to 10 pages"
JWT token missing or invalid. Extract new one.

### "Rate limited"
System has built-in rate limiting. Just wait or check logs:
```bash
docker-compose logs app | grep -i rate
```

---

## General Issues

### Check what's wrong
```bash
# View logs
docker-compose logs --tail=100 app

# Run validation
docker-compose exec app python preflight_check.py

# Check containers
docker-compose ps
```

### Try this order
1. `docker-compose restart app`
2. `docker-compose logs app` (look for errors)
3. `docker-compose down && docker-compose build && docker-compose up -d`
4. Nuclear option: `docker-compose down -v` (deletes data!)

---

## Common Error Messages

**"No such file: .env"**
→ Create `.env` from template

**"Invalid JSON"**
→ Check `service_account.json` or `brands_config.json` syntax

**"Spreadsheet not found"**
→ Check `MASTER_SPREADSHEET_NAME` in `.env` matches sheet name

**"Token expired"**
→ Extract new JWT token, update `.env`, restart

**"Module not found"**
→ Rebuild: `docker-compose build`

---

## Still Stuck?

1. Check logs: `docker-compose logs app`
2. Run validation: `docker-compose exec app python preflight_check.py`
3. Review `SETUP.md` to verify all steps completed
4. Try fresh start: `docker-compose down -v` then re-run setup