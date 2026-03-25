"""
PostgreSQL RDS integration.
Stores drift reports and fingerprints for history tracking.
Falls back gracefully when DB is not configured (local dev).
"""

import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import Optional, Dict, Any, List

from driftwatch.utils.config import (
    DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT, DB_ENABLED
)
from driftwatch.utils.logger import get_logger

logger = get_logger("database")


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    """Get a PostgreSQL connection."""
    if not DB_ENABLED:
        raise RuntimeError(
            "Database not configured. "
            "Set DB_HOST and DB_PASSWORD in .env"
        )
    return psycopg2.connect(
        host            = DB_HOST,
        database        = DB_NAME,
        user            = DB_USER,
        password        = DB_PASSWORD,
        port            = DB_PORT,
        connect_timeout = 10
    )


def check_connection() -> bool:
    """Test if database is reachable."""
    if not DB_ENABLED:
        return False
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"DB connection failed: {e}")
        return False


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    """
    Create all tables if they don't exist.
    Run this once when EC2 starts.
    """
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS drift_reports (
            id               SERIAL PRIMARY KEY,
            created_at       TIMESTAMP DEFAULT NOW(),
            tag              VARCHAR(255),
            overall_severity VARCHAR(50)  NOT NULL,
            features_checked INTEGER,
            drifted_count    INTEGER,
            drifted_features TEXT,
            reference_rows   INTEGER,
            current_rows     INTEGER,
            report_json      TEXT NOT NULL,
            alerted          BOOLEAN DEFAULT FALSE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id           VARCHAR(36) PRIMARY KEY,
            created_at   TIMESTAMP DEFAULT NOW(),
            name         VARCHAR(255),
            num_rows     INTEGER,
            num_features INTEGER,
            features     TEXT,
            stats_json   TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id         SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            report_id  INTEGER REFERENCES drift_reports(id),
            severity   VARCHAR(50),
            channel    VARCHAR(50),
            success    BOOLEAN,
            message    TEXT
        );
    """)

    # Index for fast history queries
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_created_at
        ON drift_reports(created_at DESC);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_severity
        ON drift_reports(overall_severity);
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database tables initialised successfully")


# ── Drift Reports ─────────────────────────────────────────────────────────────

def save_report(
    report: Dict[str, Any],
    tag: Optional[str] = None
) -> Optional[int]:
    """
    Save a drift report to PostgreSQL.
    Returns the report ID or None if DB not configured.
    """
    if not DB_ENABLED:
        logger.debug("DB not configured — skipping report save")
        return None

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO drift_reports
            (tag, overall_severity, features_checked,
             drifted_count, drifted_features,
             reference_rows, current_rows, report_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            tag,
            report.get("overall_severity"),
            report.get("features_checked"),
            report.get("drifted_count"),
            json.dumps(report.get("drifted_features", [])),
            report.get("reference_rows"),
            report.get("current_rows"),
            json.dumps(report, default=str),
        ))

        report_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"Report saved to DB with ID {report_id}")
        return report_id

    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        return None


def get_report_history(limit: int = 50) -> List[Dict]:
    """
    Get recent drift reports for the history dashboard.
    Returns empty list if DB not configured.
    """
    if not DB_ENABLED:
        return []

    try:
        conn = get_connection()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("""
            SELECT id, created_at, tag, overall_severity,
                   features_checked, drifted_count,
                   drifted_features, reference_rows, current_rows
            FROM drift_reports
            ORDER BY created_at DESC
            LIMIT %s;
        """, (limit,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id":               row["id"],
                "created_at":       row["created_at"].isoformat(),
                "tag":              row["tag"],
                "overall_severity": row["overall_severity"],
                "features_checked": row["features_checked"],
                "drifted_count":    row["drifted_count"],
                "drifted_features": json.loads(row["drifted_features"] or "[]"),
                "reference_rows":   row["reference_rows"],
                "current_rows":     row["current_rows"],
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []


def get_severity_trend(days: int = 7) -> List[Dict]:
    """
    Get severity counts per day for trend chart.
    Used by history dashboard.
    """
    if not DB_ENABLED:
        return []

    try:
        conn = get_connection()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("""
            SELECT
                DATE(created_at) as date,
                overall_severity,
                COUNT(*) as count
            FROM drift_reports
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at), overall_severity
            ORDER BY date DESC;
        """, (days,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "date":     str(row["date"]),
                "severity": row["overall_severity"],
                "count":    row["count"],
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to get trend: {e}")
        return []


def mark_report_alerted(report_id: int):
    """Mark a report as having sent an alert."""
    if not DB_ENABLED or not report_id:
        return
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE drift_reports SET alerted = TRUE WHERE id = %s",
            (report_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to mark alerted: {e}")


# ── Fingerprints ──────────────────────────────────────────────────────────────

def save_fingerprint_to_db(
    fp_id: str,
    name: Optional[str],
    num_rows: int,
    num_features: int,
    features: list,
    stats: dict
):
    """Save fingerprint metadata to PostgreSQL."""
    if not DB_ENABLED:
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO fingerprints
            (id, name, num_rows, num_features, features, stats_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, (
            fp_id,
            name,
            num_rows,
            num_features,
            json.dumps(features),
            json.dumps(stats, default=str),
        ))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Fingerprint {fp_id} saved to DB")

    except Exception as e:
        logger.error(f"Failed to save fingerprint: {e}")


def list_fingerprints_from_db() -> List[Dict]:
    """List all saved fingerprints from DB."""
    if not DB_ENABLED:
        return []

    try:
        conn = get_connection()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute("""
            SELECT id, created_at, name, num_rows, num_features, features
            FROM fingerprints
            ORDER BY created_at DESC;
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id":           row["id"],
                "created_at":   row["created_at"].isoformat(),
                "name":         row["name"],
                "num_rows":     row["num_rows"],
                "num_features": row["num_features"],
                "features":     json.loads(row["features"] or "[]"),
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Failed to list fingerprints: {e}")
        return []


# ── Alert Log ─────────────────────────────────────────────────────────────────

def log_alert(
    report_id: Optional[int],
    severity: str,
    channel: str,
    success: bool,
    message: str = ""
):
    """Log an alert that was sent."""
    if not DB_ENABLED:
        return

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO alert_log
            (report_id, severity, channel, success, message)
            VALUES (%s, %s, %s, %s, %s);
        """, (report_id, severity, channel, success, message))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to log alert: {e}")