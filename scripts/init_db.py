#!/usr/bin/env python3
"""
Run this ONCE on EC2 after RDS is set up.
Creates all database tables.

Usage:
    PYTHONPATH=. python scripts/init_db.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from driftwatch.utils.config import DB_ENABLED, DB_HOST, DB_NAME
from driftwatch.database.db import init_db, check_connection


def main():
    print("\nDriftWatch — Database Initialisation")
    print("=" * 45)

    if not DB_ENABLED:
        print("ERROR: Database not configured.")
        print("Set these in your .env file:")
        print("  DB_HOST=your-rds-endpoint.rds.amazonaws.com")
        print("  DB_PASSWORD=your_password")
        sys.exit(1)

    print(f"Host     : {DB_HOST}")
    print(f"Database : {DB_NAME}")
    print()

    print("Testing connection...")
    if not check_connection():
        print("ERROR: Cannot connect to database.")
        print("Check:")
        print("  1. RDS instance is running")
        print("  2. Security group allows EC2 → RDS on port 5432")
        print("  3. DB_HOST, DB_USER, DB_PASSWORD are correct")
        sys.exit(1)

    print("Connection successful")
    print()
    print("Creating tables...")

    try:
        init_db()
        print()
        print("Tables created:")
        print("  drift_reports  — stores all drift check results")
        print("  fingerprints   — stores training fingerprints")
        print("  alert_log      — stores sent alert history")
        print()
        print("Database ready.")
        print("=" * 45)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()