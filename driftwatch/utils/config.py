"""
Centralised configuration.
All environment variables read from here.
Never import os.getenv directly elsewhere — always use this.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── App ───────────────────────────────────────────────────────────────────────
PORT        = int(os.getenv("PORT", "8000"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development | production
IS_PROD     = ENVIRONMENT == "production"

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Database (RDS PostgreSQL) ─────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "")
DB_NAME     = os.getenv("DB_NAME", "driftwatch")
DB_USER     = os.getenv("DB_USER", "driftwatch_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT     = int(os.getenv("DB_PORT", "5432"))

# Whether database is configured
DB_ENABLED  = bool(DB_HOST and DB_PASSWORD)

# ── AWS ───────────────────────────────────────────────────────────────────────
AWS_REGION       = os.getenv("AWS_REGION", "ap-south-1")
S3_DATA_BUCKET   = os.getenv("S3_DATA_BUCKET", "")
SNS_TOPIC_ARN    = os.getenv("SNS_TOPIC_ARN", "")
SES_FROM_EMAIL   = os.getenv("SES_FROM_EMAIL", "")
ALERT_EMAIL      = os.getenv("ALERT_EMAIL", "")
EC2_PUBLIC_IP    = os.getenv("EC2_PUBLIC_IP", "localhost")

# Whether AWS alerting is configured
ALERTS_ENABLED   = bool(SNS_TOPIC_ARN and AWS_REGION)

# Whether S3 storage is configured
S3_ENABLED       = bool(S3_DATA_BUCKET and AWS_REGION)

# ── Drift thresholds ──────────────────────────────────────────────────────────
PSI_WARNING_THRESHOLD  = float(os.getenv("PSI_WARNING_THRESHOLD",  "0.10"))
PSI_CRITICAL_THRESHOLD = float(os.getenv("PSI_CRITICAL_THRESHOLD", "0.20"))
ANOMALY_THRESHOLD      = float(os.getenv("ANOMALY_THRESHOLD",      "-0.15"))
NEGATIVE_RATIO_THRESHOLD = float(os.getenv("NEGATIVE_RATIO_THRESHOLD", "0.6"))

# ── Misc ──────────────────────────────────────────────────────────────────────
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "60"))