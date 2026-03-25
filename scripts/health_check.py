#!/usr/bin/env python3
"""
Health check script.
AWS Load Balancer calls GET /health every 30 seconds.
This verifies all components are working.

Usage:
    PYTHONPATH=. python scripts/health_check.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from driftwatch.utils.config import PORT, DB_ENABLED
from driftwatch.database.db import check_connection


def main():
    print("\nDriftWatch — Health Check")
    print("=" * 40)

    all_ok = True

    # 1. API health
    try:
        r = requests.get(
            f"http://localhost:{PORT}/api/v1/health",
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            print(f"API          : OK (v{data.get('version')})")
        else:
            print(f"API          : FAIL (status {r.status_code})")
            all_ok = False
    except Exception as e:
        print(f"API          : FAIL ({e})")
        all_ok = False

    # 2. Database
    if DB_ENABLED:
        if check_connection():
            print("Database     : OK")
        else:
            print("Database     : FAIL (cannot connect to RDS)")
            all_ok = False
    else:
        print("Database     : SKIP (not configured)")

    # 3. Stats endpoint
    try:
        r = requests.get(
            f"http://localhost:{PORT}/api/v1/stats",
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            print(f"Stats        : OK ({data.get('fingerprints_stored')} fingerprints)")
        else:
            print(f"Stats        : FAIL (status {r.status_code})")
            all_ok = False
    except Exception as e:
        print(f"Stats        : FAIL ({e})")
        all_ok = False

    print("=" * 40)

    if all_ok:
        print("Overall: HEALTHY")
        sys.exit(0)
    else:
        print("Overall: UNHEALTHY")
        sys.exit(1)


if __name__ == "__main__":
    main()