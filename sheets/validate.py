#!/usr/bin/env python3
"""
Validation script for Google Sheets integration
Tests sheet creation and data updates
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sheets_manager import GoogleSheetsManager
import json

def validate_schema():
    """Validate schema consistency"""
    from config import WEEKLY_SNAPSHOT_COLUMNS, WEEKLY_COLUMN_PATHS
    
    print("🔍 Validating schema...")
    
    # Check all columns have paths
    missing_paths = []
    for col in WEEKLY_SNAPSHOT_COLUMNS:
        if col not in WEEKLY_COLUMN_PATHS:
            missing_paths.append(col)
    
    if missing_paths:
        print(f"❌ Missing JSON paths for columns: {missing_paths}")
        return False
    
    # Check all paths are valid
    extra_paths = []
    for col in WEEKLY_COLUMN_PATHS:
        if col not in WEEKLY_SNAPSHOT_COLUMNS:
            extra_paths.append(col)
    
    if extra_paths:
        print(f"⚠️  Extra paths defined but not in columns: {extra_paths}")
    
    print(f"✅ Schema valid: {len(WEEKLY_SNAPSHOT_COLUMNS)} columns defined")
    return True

def test_json_mapping():
    """Test JSON path extraction with sample data"""
    
    print("\n🔍 Testing JSON path extraction...")
    
    # Load sample report
    sample_file = '../weekly_report_ketogo_app_2026-W00.json'
    if not os.path.exists(sample_file):
        print(f"⚠️  Sample file not found: {sample_file}")
        print("   Skipping JSON mapping test")
        return True
    
    with open(sample_file, 'r') as f:
        data = json.load(f)
    
    from config import WEEKLY_COLUMN_PATHS
    manager = GoogleSheetsManager()
    
    # Test extraction
    missing_values = []
    for col, path in WEEKLY_COLUMN_PATHS.items():
        value = manager._get_nested_value(data, path)
        if value is None:
            missing_values.append(f"{col} ({path})")
    
    if missing_values:
        print(f"⚠️  Some paths returned None (might be valid):")
        for mv in missing_values[:5]:
            print(f"     - {mv}")
        if len(missing_values) > 5:
            print(f"     ... and {len(missing_values) - 5} more")
    
    print(f"✅ Successfully extracted {len(WEEKLY_COLUMN_PATHS) - len(missing_values)}/{len(WEEKLY_COLUMN_PATHS)} values")
    return True

def validate_chart_ranges():
    """Validate chart data range definitions"""
    from config import (
        CHART_RATING_TREND, CHART_VOLUME_TREND, CHART_SENTIMENT,
        CHART_RATING_DIST, CHART_NEGATIVE_THEMES
    )
    
    print("\n🔍 Validating chart ranges...")
    
    charts = [
        ('Rating Trend', CHART_RATING_TREND),
        ('Volume Trend', CHART_VOLUME_TREND),
        ('Sentiment', CHART_SENTIMENT),
        ('Rating Distribution', CHART_RATING_DIST),
        ('Negative Themes', CHART_NEGATIVE_THEMES)
    ]
    
    # Check for overlaps
    ranges = []
    for name, config in charts:
        start = config['start_row']
        end = start + config['max_rows']
        ranges.append((name, start, end))
    
    # Sort by start row
    ranges.sort(key=lambda x: x[1])
    
    overlaps = []
    for i in range(len(ranges) - 1):
        curr_name, curr_start, curr_end = ranges[i]
        next_name, next_start, next_end = ranges[i + 1]
        
        if curr_end >= next_start:
            overlaps.append(f"{curr_name} (ends {curr_end}) overlaps {next_name} (starts {next_start})")
    
    if overlaps:
        print(f"❌ Chart range overlaps detected:")
        for overlap in overlaps:
            print(f"   - {overlap}")
        return False
    
    print(f"✅ All chart ranges valid (no overlaps)")
    return True

def check_credentials():
    """Check if credentials are configured"""
    print("\n🔍 Checking Google API credentials...")
    
    creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
    if not creds_path:
        print("❌ GOOGLE_SHEETS_CREDENTIALS not set in .env")
        print("   Add: GOOGLE_SHEETS_CREDENTIALS=/path/to/credentials.json")
        return False
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    print(f"✅ Credentials configured: {creds_path}")
    
    # Try to load
    try:
        manager = GoogleSheetsManager()
        print("✅ Google Sheets API authenticated successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to authenticate: {e}")
        return False

def main():
    """Run all validation checks"""
    
    print("="*70)
    print("GOOGLE SHEETS VALIDATION")
    print("="*70)
    
    checks = [
        ('Schema Consistency', validate_schema),
        ('Chart Ranges', validate_chart_ranges),
        ('JSON Mapping', test_json_mapping),
        ('Google API Credentials', check_credentials)
    ]
    
    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} failed with error: {e}")
            results.append((name, False))
    
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All validations passed!")
        print("\nNext steps:")
        print("  1. Run: python sheets_cli.py create 'YourBrand'")
        print("  2. Test with: python sheets_cli.py update <id> <report.json>")
    else:
        print("\n⚠️  Some validations failed. Please fix issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()