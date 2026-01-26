# main.py
from db import Database
from scraper import TrustpilotScraper

# Initialize
db = Database()
scraper = TrustpilotScraper(db)

# Scrape and save in batches (saves every 100 reviews)
company_domain = "ketogo.app"

# Auto-detect mode (checks if brand exists in DB)
# scraper.scrape_and_save(company_domain, batch_size=100)

# Or force full history scrape (even if brand exists)
scraper.scrape_and_save(company_domain, use_date_filter=False, batch_size=100)

# Or force incremental (last 30 days only)
# scraper.scrape_and_save(company_domain, use_date_filter=True, batch_size=100)

# Close connection
db.close()