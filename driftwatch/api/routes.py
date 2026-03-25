"""
API route handlers — updated with RDS + email alerts.
"""

import os
import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from driftwatch.api.models import (
    CheckRequest, FingerprintRequest, CompareRequest, ExplainRequest,
    DriftReportResponse, FingerprintResponse, HealthResponse, ErrorResponse
)
from driftwatch.engine import DriftEngine
from driftwatch.detectors.schema import get_feature_stats
from driftwatch.explainer.claude_client import ClaudeExplainer
from driftwatch.utils.config import DB_ENABLED, ALERTS_ENABLED
from driftwatch.utils.logger import get_logger
from driftwatch.database.db import (
    save_report, get_report_history, get_severity_trend,
    save_fingerprint_to_db, list_fingerprints_from_db,
    check_connection, mark_report_alerted, log_alert
)
from driftwatch.alerts.email_alert import send_drift_alert
from driftwatch.utils.s3_client import s3

logger    = get_logger("api.routes")
router    = APIRouter()
engine    = DriftEngine()
explainer = ClaudeExplainer()
_fingerprints: Dict[str, Dict] = {}


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        explainer_available=explainer.available
    )


@router.post("/check", response_model=DriftReportResponse, tags=["Drift"])
async def check_drift(req: CheckRequest, background_tasks: BackgroundTasks):
    try:
        train_df   = pd.DataFrame(req.training)
        serving_df = pd.DataFrame(req.serving)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse data: {e}")

    if train_df.empty or serving_df.empty:
        raise HTTPException(status_code=422, detail="Data must not be empty.")

    report = engine.analyze(train_df, serving_df, label_column=req.label_column)
    result = report.to_dict()

    if req.explain:
        exp = explainer.explain_report(result)
        result["explanation"] = {
            "summary":   exp.summary,
            "full_text": exp.full_text,
            "used_llm":  exp.used_llm,
            "model":     exp.model,
        }

    background_tasks.add_task(_save_and_alert, result)
    return JSONResponse(content=result)


async def _save_and_alert(result: dict):
    report_id = save_report(result)
    severity  = result.get("overall_severity")
    if severity in ("critical", "warning"):
        success = send_drift_alert(result, report_id=report_id)
        if report_id:
            mark_report_alerted(report_id)
            log_alert(report_id, severity, "email", success, "")
            
    # Also save full report to S3 for long-term storage
    if s3.enabled:
        rid = result.get('id') or str(uuid.uuid4())
        report_key = f"reports/{result.get('timestamp')[:10]}/{rid}.json"
        s3.upload_json(report_key, result)


@router.get("/history", tags=["History"])
async def get_history(limit: int = 50):
    reports = get_report_history(limit=limit)
    return {"reports": reports, "count": len(reports), "db_enabled": DB_ENABLED}


@router.get("/history/trend", tags=["History"])
async def get_trend(days: int = 7):
    trend = get_severity_trend(days=days)
    return {"trend": trend, "days": days}


@router.post("/fingerprint", response_model=FingerprintResponse, tags=["Fingerprint"])
async def create_fingerprint(req: FingerprintRequest):
    try:
        df = pd.DataFrame(req.data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse data: {e}")

    if req.label_column and req.label_column in df.columns:
        df = df.drop(columns=[req.label_column])

    fp_id   = str(uuid.uuid4())
    created = datetime.utcnow().isoformat()
    stats   = get_feature_stats(df)

    _fingerprints[fp_id] = {
        "id": fp_id, "created_at": created, "name": req.name,
        "num_rows": len(df), "num_features": len(df.columns),
        "features": list(df.columns), "stats": stats, "_dataframe": df,
    }

    save_fingerprint_to_db(fp_id, req.name, len(df), len(df.columns), list(df.columns), stats)

    # Save to S3 if enabled
    if s3.enabled:
        s3.upload_json(f"fingerprints/{fp_id}.json", {**_fingerprints[fp_id], "_dataframe": None})
        # Optionally upload the actual data if it's small or required
        # s3.upload_csv(f"data/training/{fp_id}.csv", df)

    return FingerprintResponse(
        id=fp_id, created_at=created, name=req.name,
        num_rows=len(df), num_features=len(df.columns), features=list(df.columns),
    )


@router.get("/fingerprint/{fp_id}", response_model=FingerprintResponse, tags=["Fingerprint"])
async def get_fingerprint(fp_id: str):
    if fp_id not in _fingerprints:
        raise HTTPException(status_code=404, detail=f"Fingerprint '{fp_id}' not found.")
    fp = _fingerprints[fp_id]
    return FingerprintResponse(
        id=fp["id"], created_at=fp["created_at"], name=fp.get("name"),
        num_rows=fp["num_rows"], num_features=fp["num_features"], features=fp["features"],
    )


@router.get("/fingerprints", tags=["Fingerprint"])
async def list_fingerprints():
    memory_fps = [{"id": fp["id"], "created_at": fp["created_at"], "name": fp.get("name"), "features": fp["features"], "num_rows": fp["num_rows"], "source": "memory"} for fp in _fingerprints.values()]
    db_fps     = [{**fp, "source": "database"} for fp in list_fingerprints_from_db()]
    seen, merged = set(), []
    for fp in memory_fps + db_fps:
        if fp["id"] not in seen:
            seen.add(fp["id"]); merged.append(fp)
    return merged


@router.delete("/fingerprint/{fp_id}", tags=["Fingerprint"])
async def delete_fingerprint(fp_id: str):
    if fp_id not in _fingerprints:
        raise HTTPException(status_code=404, detail=f"Fingerprint '{fp_id}' not found.")
    del _fingerprints[fp_id]
    return {"deleted": fp_id}


@router.post("/compare", response_model=DriftReportResponse, tags=["Drift"])
async def compare_with_fingerprint(req: CompareRequest, background_tasks: BackgroundTasks):
    if req.fingerprint_id not in _fingerprints:
        raise HTTPException(status_code=404, detail=f"Fingerprint '{req.fingerprint_id}' not found.")

    fp = _fingerprints[req.fingerprint_id]
    try:
        serving_df = pd.DataFrame(req.serving)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse data: {e}")

    report = engine.analyze(fp["_dataframe"], serving_df)
    result = report.to_dict()

    if req.explain:
        exp = explainer.explain_report(result)
        result["explanation"] = {"summary": exp.summary, "full_text": exp.full_text, "used_llm": exp.used_llm, "model": exp.model}

    background_tasks.add_task(_save_and_alert, result)
    return JSONResponse(content=result)


@router.post("/explain", tags=["Explain"])
async def explain_report(req: ExplainRequest):
    if req.feature:
        features = req.report.get("features", {})
        if req.feature not in features:
            raise HTTPException(status_code=404, detail=f"Feature '{req.feature}' not in report.")
        exp = explainer.explain_feature(req.feature, features[req.feature])
    else:
        exp = explainer.explain_report(req.report)
    return {"summary": exp.summary, "full_text": exp.full_text, "used_llm": exp.used_llm, "model": exp.model, "feature": exp.feature}


@router.get("/stats", tags=["System"])
async def get_stats():
    return {
        "fingerprints_stored": len(_fingerprints),
        "explainer_available": explainer.available,
        "explainer_model":     ClaudeExplainer.MODEL,
        "db_enabled":          DB_ENABLED,
        "alerts_enabled":      ALERTS_ENABLED,
        "db_connected":        check_connection() if DB_ENABLED else False,
        "version":             "0.1.0",
    }


@router.post("/test-alert", tags=["System"])
async def test_alert():
    from driftwatch.alerts.email_alert import send_test_alert
    success = send_test_alert()
    return {"success": success, "message": "Check your email" if success else "Failed — check SNS_TOPIC_ARN"}