"""
Email alert system for DriftWatch.
Uses AWS SNS → SES to send drift alerts.
Falls back gracefully when AWS not configured.
"""

import boto3
import json
from datetime import datetime
from typing import Dict, Any, Optional

from driftwatch.utils.config import (
    AWS_REGION, SNS_TOPIC_ARN, SES_FROM_EMAIL,
    ALERT_EMAIL, EC2_PUBLIC_IP, ALERTS_ENABLED
)
from driftwatch.utils.logger import get_logger

logger = get_logger("alerts")


# ── Core Alert Function ───────────────────────────────────────────────────────

def send_drift_alert(
    report: Dict[str, Any],
    report_id: Optional[int] = None
) -> bool:
    """
    Send email alert when drift is detected.

    Flow: DriftWatch detects drift
          → This function builds the email
          → Publishes to SNS topic
          → SNS delivers to your email via subscription

    Returns True if alert sent successfully.
    """
    severity = report.get("overall_severity", "stable")

    # Only alert on warning or critical
    if severity not in ("critical", "warning"):
        logger.debug(f"No alert needed — severity is {severity}")
        return False

    # Skip if AWS not configured
    if not ALERTS_ENABLED:
        logger.warning(
            "AWS alerts not configured. "
            "Set SNS_TOPIC_ARN and AWS_REGION in .env"
        )
        _log_to_console(report, severity)
        return False

    subject = _build_subject(report, severity)
    body    = _build_email_body(report, severity, report_id)

    success = _publish_to_sns(subject, body)

    if success:
        logger.info(f"Alert sent — {severity.upper()} drift detected")
    else:
        logger.error("Alert failed — check SNS configuration")

    return success


# ── Email Builder ─────────────────────────────────────────────────────────────

def _build_subject(report: Dict, severity: str) -> str:
    drifted  = report.get("drifted_features", [])
    n        = len(drifted)
    worst    = drifted[0] if drifted else "unknown"
    icon     = "🔴" if severity == "critical" else "🟡"
    return (
        f"{icon} [DriftWatch] {severity.upper()} — "
        f"{n} feature{'s' if n != 1 else ''} drifted "
        f"(worst: {worst})"
    )


def _build_email_body(
    report: Dict,
    severity: str,
    report_id: Optional[int]
) -> str:
    """Build a clean, readable email body."""

    drifted   = report.get("drifted_features", [])
    features  = report.get("features", {})
    schema    = report.get("schema", {})
    n_train   = report.get("reference_rows", 0)
    n_serve   = report.get("current_rows", 0)
    timestamp = report.get("timestamp", datetime.utcnow().isoformat())
    exp       = report.get("explanation", {})

    sep  = "─" * 52
    sep2 = "═" * 52

    lines = [
        sep2,
        f"  DRIFTWATCH ALERT — {severity.upper()}",
        sep2,
        f"",
        f"  Time      : {timestamp[:19].replace('T', ' ')} UTC",
        f"  Severity  : {severity.upper()}",
        f"  Training  : {n_train:,} rows",
        f"  Serving   : {n_serve:,} rows",
        f"  Report ID : {report_id or 'N/A'}",
        f"",
    ]

    # Schema issues
    if schema.get("has_drift"):
        lines += [sep, "  SCHEMA ISSUES", sep]
        for issue in schema.get("issues", [])[:5]:
            lines.append(f"  [{issue['severity'].upper()}] {issue['detail']}")
        lines.append("")

    # Drifted features
    if drifted:
        lines += [sep, "  DRIFTED FEATURES", sep]
        for feat in drifted[:8]:
            data = features.get(feat, {})
            ftype = data.get("type", "unknown")

            if ftype == "numerical":
                psi      = data.get("psi", "N/A")
                ref_mean = data.get("ref_mean")
                cur_mean = data.get("cur_mean")
                line     = f"  {feat:<28} PSI={psi}"
                if ref_mean and cur_mean and ref_mean != 0:
                    delta = ((cur_mean - ref_mean) / abs(ref_mean)) * 100
                    line += f"  mean {delta:+.1f}%"
                lines.append(line)

            elif ftype == "categorical":
                p_val = data.get("chi2_test", {}).get("p_value", "N/A")
                lines.append(f"  {feat:<28} p={p_val}  category shift")

        lines.append("")

    # LLM Explanation
    if exp and exp.get("full_text"):
        lines += [sep, "  ANALYSIS", sep]
        lines.append(f"  {exp.get('summary', '')}")
        lines.append("")

        for line in exp.get("full_text", "").split("\n"):
            stripped = line.strip()
            if stripped.startswith(("DIAGNOSIS", "IMPACT", "ACTION")):
                lines += ["", f"  {stripped}"]
            elif stripped.startswith(("1.", "2.", "3.", "4.", "5.")):
                lines.append(f"    {stripped}")
            elif stripped and not stripped.startswith("DIAGNOSIS"):
                lines.append(f"    {stripped}")

        lines.append("")

    # Links
    dashboard_url = f"http://{EC2_PUBLIC_IP}:3000"
    api_url       = f"http://{EC2_PUBLIC_IP}:8000/docs"

    lines += [
        sep,
        "  LINKS",
        sep,
        f"  Dashboard : {dashboard_url}",
        f"  API Docs  : {api_url}",
        f"  History   : {api_url.replace('/docs', '/api/v1/history')}",
        f"",
        sep2,
        f"  DriftWatch v0.1.0 — Real-Time ML Drift Detection",
        f"  This alert was triggered automatically.",
        sep2,
    ]

    return "\n".join(lines)


# ── SNS Publisher ─────────────────────────────────────────────────────────────

def _publish_to_sns(subject: str, message: str) -> bool:
    """Publish alert to AWS SNS topic."""
    try:
        sns = boto3.client("sns", region_name=AWS_REGION)
        response = sns.publish(
            TopicArn = SNS_TOPIC_ARN,
            Subject  = subject[:100],  # SNS subject limit
            Message  = message,
        )
        message_id = response.get("MessageId")
        logger.info(f"SNS published — MessageId: {message_id}")
        return True

    except Exception as e:
        logger.error(f"SNS publish failed: {e}")
        return False


# ── Console Fallback ──────────────────────────────────────────────────────────

def _log_to_console(report: Dict, severity: str):
    """
    When AWS not configured — log alert to console.
    Useful for local development.
    """
    drifted = report.get("drifted_features", [])
    print(f"\n{'='*52}")
    print(f"  DRIFTWATCH ALERT [{severity.upper()}]")
    print(f"  Drifted features: {', '.join(drifted)}")
    print(f"  (Configure SNS_TOPIC_ARN to send email alerts)")
    print(f"{'='*52}\n")


# ── Test Alert ────────────────────────────────────────────────────────────────

def send_test_alert() -> bool:
    """
    Send a test alert to verify SNS is configured correctly.
    Call this from CLI: python -c "from driftwatch.alerts.email_alert import send_test_alert; send_test_alert()"
    """
    test_report = {
        "timestamp":        datetime.utcnow().isoformat(),
        "overall_severity": "warning",
        "features_checked": 3,
        "drifted_count":    1,
        "drifted_features": ["transaction_amount"],
        "reference_rows":   1000,
        "current_rows":     500,
        "schema":           {"has_drift": False, "issues": [], "critical_count": 0, "warning_count": 0},
        "features": {
            "transaction_amount": {
                "type":     "numerical",
                "severity": "warning",
                "psi":      0.18,
                "ref_mean": 145.0,
                "cur_mean": 210.0,
            }
        },
        "explanation": {
            "summary":   "Test alert — DriftWatch is configured correctly",
            "full_text": "DIAGNOSIS\n  This is a test alert.\nIMPACT\n  No action needed.\nACTION\n  1. Confirm you received this email",
            "used_llm":  False,
            "model":     "rule-based",
        }
    }

    logger.info("Sending test alert...")
    result = send_drift_alert(test_report, report_id=0)
    if result:
        logger.info("Test alert sent successfully — check your email")
    else:
        logger.warning("Test alert failed — check SNS configuration")
    return result