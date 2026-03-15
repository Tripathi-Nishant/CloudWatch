"""
API route handlers.
Each route is thin — validate input, call engine, return response.
Business logic lives in engine.py and explainer/, not here.
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

router   = APIRouter()
engine   = DriftEngine()
explainer = ClaudeExplainer()

# In-memory fingerprint store
# In production you'd swap this for Redis or a database
_fingerprints: Dict[str, Dict] = {}


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check — confirms API is up and explainer availability."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        explainer_available=explainer.available
    )


# ── Core drift check ──────────────────────────────────────────────────────────

@router.post("/check", response_model=DriftReportResponse, tags=["Drift"])
async def check_drift(req: CheckRequest):
    """
    Compare training and serving data.
    Returns a full drift report including per-feature statistics.
    """
    try:
        train_df   = pd.DataFrame(req.training)
        serving_df = pd.DataFrame(req.serving)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse data: {e}")

    if train_df.empty or serving_df.empty:
        raise HTTPException(status_code=422, detail="Training and serving data must not be empty.")

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

    return JSONResponse(content=result)


# ── Fingerprint ───────────────────────────────────────────────────────────────

@router.post("/fingerprint", response_model=FingerprintResponse, tags=["Fingerprint"])
async def create_fingerprint(req: FingerprintRequest):
    """
    Save a statistical fingerprint of your training data.
    Returns an ID you can use with /compare — no need to store raw training data.
    """
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
        "id":           fp_id,
        "created_at":   created,
        "name":         req.name,
        "num_rows":     len(df),
        "num_features": len(df.columns),
        "features":     list(df.columns),
        "stats":        stats,
        "_dataframe":   df,    # keep raw df in memory for accurate comparison
    }

    return FingerprintResponse(
        id=fp_id,
        created_at=created,
        name=req.name,
        num_rows=len(df),
        num_features=len(df.columns),
        features=list(df.columns),
    )


@router.get("/fingerprint/{fp_id}", response_model=FingerprintResponse, tags=["Fingerprint"])
async def get_fingerprint(fp_id: str):
    """Get metadata for a saved fingerprint."""
    if fp_id not in _fingerprints:
        raise HTTPException(status_code=404, detail=f"Fingerprint '{fp_id}' not found.")
    fp = _fingerprints[fp_id]
    return FingerprintResponse(
        id=fp["id"],
        created_at=fp["created_at"],
        name=fp.get("name"),
        num_rows=fp["num_rows"],
        num_features=fp["num_features"],
        features=fp["features"],
    )


@router.get("/fingerprints", tags=["Fingerprint"])
async def list_fingerprints():
    """List all saved fingerprints."""
    return [
        {
            "id":         fp["id"],
            "created_at": fp["created_at"],
            "name":       fp.get("name"),
            "features":   fp["features"],
            "num_rows":   fp["num_rows"],
        }
        for fp in _fingerprints.values()
    ]


@router.delete("/fingerprint/{fp_id}", tags=["Fingerprint"])
async def delete_fingerprint(fp_id: str):
    """Delete a saved fingerprint."""
    if fp_id not in _fingerprints:
        raise HTTPException(status_code=404, detail=f"Fingerprint '{fp_id}' not found.")
    del _fingerprints[fp_id]
    return {"deleted": fp_id}


# ── Compare against fingerprint ───────────────────────────────────────────────

@router.post("/compare", response_model=DriftReportResponse, tags=["Drift"])
async def compare_with_fingerprint(req: CompareRequest):
    """
    Compare serving data against a previously saved fingerprint.
    Ideal for production pipelines where you don't want to store raw training data.
    """
    if req.fingerprint_id not in _fingerprints:
        raise HTTPException(
            status_code=404,
            detail=f"Fingerprint '{req.fingerprint_id}' not found. POST /fingerprint first."
        )

    fp = _fingerprints[req.fingerprint_id]
    reference_df = fp["_dataframe"]

    try:
        serving_df = pd.DataFrame(req.serving)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse serving data: {e}")

    report = engine.analyze(reference_df, serving_df)
    result = report.to_dict()

    if req.explain:
        exp = explainer.explain_report(result)
        result["explanation"] = {
            "summary":   exp.summary,
            "full_text": exp.full_text,
            "used_llm":  exp.used_llm,
            "model":     exp.model,
        }

    return JSONResponse(content=result)


# ── Explanation ───────────────────────────────────────────────────────────────

@router.post("/explain", tags=["Explain"])
async def explain_report(req: ExplainRequest):
    """
    Generate an LLM explanation for an existing drift report.
    Pass the full report dict from a previous /check or /compare call.
    """
    if req.feature:
        features = req.report.get("features", {})
        if req.feature not in features:
            raise HTTPException(
                status_code=404,
                detail=f"Feature '{req.feature}' not in report."
            )
        feat_data = features[req.feature]
        exp = explainer.explain_feature(req.feature, feat_data)
    else:
        exp = explainer.explain_report(req.report)

    return {
        "summary":   exp.summary,
        "full_text": exp.full_text,
        "used_llm":  exp.used_llm,
        "model":     exp.model,
        "feature":   exp.feature,
    }


# ── Stats summary for dashboard ───────────────────────────────────────────────

@router.get("/stats", tags=["System"])
async def get_stats():
    """
    Summary stats for the dashboard header cards.
    Returns total fingerprints stored and API status.
    """
    return {
        "fingerprints_stored": len(_fingerprints),
        "explainer_available": explainer.available,
        "explainer_model":     ClaudeExplainer.MODEL,
        "version":             "0.1.0",
    }