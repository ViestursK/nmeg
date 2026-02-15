#!/usr/bin/env python3
"""
Quick test: Scrape one brand in incremental mode
Tests batching + early stopping
"""

from db.database import Database
from scraper import TrustpilotScraper

print("\n" + "="*70)
print("TESTING SCRAPER WITH BATCHING")
print("="*70 + "\n")

# Initialize
db = Database()
db.connect()
scraper = TrustpilotScraper(db)

# Test incremental scrape (should use early stopping)
print("📊 Test 1: Incremental scrape (last 30 days)\n")
scraper.scrape_and_save("ketogo.app", use_date_filter=True, batch_size=50)

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
print("\nLook for:")
print("  • 'Buffered: X' in progress output (proves batching works)")
print("  • 'Early stop: 2 consecutive pages' (proves early stop works)")
print("  • Final commit of remaining batch")
print("\n")

db.close()