#!/usr/bin/env python3
"""
Pre-Submission Validation Checklist
Run this to verify everything works before submitting to client
"""

import os
import sys
import subprocess

def run_command(cmd, description):
    """Run command and report status"""
    print(f"\n{'='*70}")
    print(f"STEP: {description}")
    print(f"{'='*70}\n")
    print(f"Running: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print(f"\n✅ PASSED: {description}")
        return True
    else:
        print(f"\n❌ FAILED: {description}")
        return False


def main():
    print("\n" + "="*70)
    print("PRE-SUBMISSION VALIDATION CHECKLIST")
    print("="*70 + "\n")
    
    results = []
    
    # Step 1: Environment check
    results.append(run_command(
        "python preflight_check.py",
        "Environment & Configuration Check"
    ))
    
    if not results[-1]:
        print("\n⚠️  Fix configuration issues before continuing")
        return 1
    
    # Step 2: JWT validity
    results.append(run_command(
        "python tests/test_jwt.py",
        "JWT Token Validity Check"
    ))
    
    # Step 3: Test scraper with batching
    results.append(run_command(
        "python -m tests.test_batching",
        "Scraper Batching & Early Stop Test"
    ))
    
    # Step 4: Test weekly report generation
    input("\n⏸️  Press Enter to test weekly report generation...")
    results.append(run_command(
        "python weekly_job.py --week 2026-W06",
        "Weekly Report Generation & Upload Test"
    ))
    
    # Step 5: Optional - backfill check (can be skipped if already done)
    response = input("\n❓ Run backfill test? (y/n): ")
    if response.lower() == 'y':
        results.append(run_command(
            "python weekly_job.py --backfill --weeks 2",
            "Backfill Test (2 weeks)"
        ))
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70 + "\n")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("\n✅ ALL CHECKS PASSED!")
        print("\nFinal steps:")
        print("  1. Review any issues")
        print("  2. Check Google Sheets dashboard")
        print("  3. Install cron: bash setup_cron.sh")
        print("  4. Verify cron: crontab -l")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED - Review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())