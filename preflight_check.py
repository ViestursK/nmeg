#!/usr/bin/env python3
"""
Pre-flight Check - Verify everything is configured correctly
Docker-aware version - works both inside and outside containers
"""

import os
import sys
import json

def check_env_file():
    """Check environment variables (from .env file or Docker)"""
    
    # Detect if running in Docker
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
    
    if in_docker:
        print("🔍 Checking environment variables (Docker mode)...")
    else:
        print("🔍 Checking .env file...")
        
        if not os.path.exists('.env'):
            print("  ❌ .env file not found")
            return False
        
        from dotenv import load_dotenv
        load_dotenv()
    
    required = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASS',
        'GOOGLE_DRIVE_FOLDER_ID', 'GOOGLE_SHEETS_CREDENTIALS',
        'MASTER_SPREADSHEET_NAME'
    ]
    
    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"  ❌ Missing variables: {', '.join(missing)}")
        return False
    
    if in_docker:
        print("  ✅ All required environment variables present (from docker-compose)")
    else:
        print("  ✅ All required environment variables present")
    return True


def check_brands_config():
    """Check brands_config.json exists and is valid"""
    print("\n🔍 Checking brands_config.json...")
    
    if not os.path.exists('brands_config.json'):
        print("  ❌ brands_config.json not found")
        return False
    
    try:
        with open('brands_config.json', 'r') as f:
            config = json.load(f)
            brands = config.get('brands', [])
            
            if not brands:
                print("  ❌ No brands in config")
                return False
            
            print(f"  ✅ Found {len(brands)} brands:")
            for brand in brands:
                print(f"     • {brand.get('name')} ({brand.get('domain')})")
            return True
            
    except Exception as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False


def check_google_credentials():
    """Check Google credentials file exists"""
    print("\n🔍 Checking Google credentials...")
    
    # Try to load from environment first (works in Docker)
    creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
    # Fallback to loading from .env (outside Docker)
    if not creds_path:
        from dotenv import load_dotenv
        load_dotenv()
        creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
    
    if not creds_path:
        print("  ❌ GOOGLE_SHEETS_CREDENTIALS not set")
        return False
    
    # Handle relative paths
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(os.getcwd(), creds_path)
    
    if not os.path.exists(creds_path):
        print(f"  ❌ Credentials file not found: {creds_path}")
        return False
    
    print(f"  ✅ Credentials file exists: {creds_path}")
    return True


def check_database():
    """Check database connection"""
    print("\n🔍 Checking database connection...")
    
    try:
        from db.database import Database
        db = Database()
        db.connect()
        
        # Check tables exist
        result = db.query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        tables = [row['table_name'] for row in result]
        required_tables = ['companies', 'reviews', 'ai_summaries', 'topics']
        
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"  ❌ Missing tables: {', '.join(missing_tables)}")
            print("     Run: docker-compose exec app python -m db.setup")
            db.close()
            return False
        
        # Check topics populated
        topics_count = db.query("SELECT COUNT(*) as count FROM topics")[0]['count']
        if topics_count == 0:
            print("  ⚠️  Topics table empty - run: docker-compose exec app python -m db.import_topics")
        
        db.close()
        print("  ✅ Database connected, all tables present")
        if topics_count > 0:
            print(f"     Topics: {topics_count}")
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def check_python_packages():
    """Check required packages installed"""
    print("\n🔍 Checking Python packages...")
    
    required = [
        'psycopg2',
        'dotenv',
        'requests',
        'bs4',
        'gspread',
        'google.auth'
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"  ❌ Missing packages: {', '.join(missing)}")
        print("     Run: pip install -r requirements.txt")
        return False
    
    print("  ✅ All required packages installed")
    return True


def main():
    """Run all checks"""
    
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'
    
    print("\n" + "="*70)
    if in_docker:
        print("PRE-FLIGHT CHECK - Docker Container")
    else:
        print("PRE-FLIGHT CHECK - Local Environment")
    print("="*70 + "\n")
    
    checks = [
        check_python_packages,
        check_env_file,
        check_brands_config,
        check_google_credentials,
        check_database
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"  ❌ Check failed: {e}")
            results.append(False)
    
    print("\n" + "="*70)
    
    if all(results):
        print("✅ ALL CHECKS PASSED - Ready to run!")
        print("="*70)
        print("\nNext steps:")
        if in_docker:
            print("  1. Test run: docker-compose exec app python weekly_job.py --week 2026-W06")
            print("  2. Backfill: docker-compose exec app python weekly_job.py --backfill")
        else:
            print("  1. Start containers: docker-compose up -d")
            print("  2. Test run: python weekly_job.py --week 2026-W06")
            print("  3. Backfill: python weekly_job.py --backfill")
        print()
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Fix issues above")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())