"""
Pydantic models for all API request/response shapes.
Strict typing means bad requests fail fast with clear error messages.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


# ── Requests ──────────────────────────────────────────────────────────────────

class CheckRequest(BaseModel):
    """
    POST /check
    Send training + serving data as JSON records.
    """
    training: List[Dict[str, Any]] = Field(
        ...,
        description="Training data rows as list of dicts",
        min_length=1
    )
    serving: List[Dict[str, Any]] = Field(
        ...,
        description="Serving data rows as list of dicts",
        min_length=1
    )
    label_column: Optional[str] = Field(
        None,
        description="Column to exclude from drift checks (your target/label)"
    )
    bins: int = Field(10, ge=2, le=100, description="Histogram bins for PSI")
    explain: bool = Field(False, description="Generate LLM explanation")


class FingerprintRequest(BaseModel):
    """POST /fingerprint — save a fingerprint of training data."""
    data: List[Dict[str, Any]] = Field(..., min_length=1)
    label_column: Optional[str] = None
    name: Optional[str] = Field(None, description="Human-readable name for this fingerprint")


class CompareRequest(BaseModel):
    """POST /compare — compare serving data against a saved fingerprint."""
    fingerprint_id: str = Field(..., description="ID returned by POST /fingerprint")
    serving: List[Dict[str, Any]] = Field(..., min_length=1)
    explain: bool = False


class ExplainRequest(BaseModel):
    """POST /explain — generate explanation for an existing report."""
    report: Dict[str, Any] = Field(..., description="Full report dict from a previous check")
    feature: Optional[str] = Field(None, description="If set, explain only this feature")


# ── Responses ─────────────────────────────────────────────────────────────────

class SchemaIssue(BaseModel):
    column: str
    issue: str
    severity: str
    detail: str


class SchemaResult(BaseModel):
    has_drift: bool
    critical_count: int
    warning_count: int
    overall_severity: str
    issues: List[SchemaIssue]


class FeatureResult(BaseModel):
    type: str
    severity: str
    psi: Optional[float] = None
    kl_divergence: Optional[float] = None
    js_distance: Optional[float] = None
    ref_mean: Optional[float] = None
    cur_mean: Optional[float] = None
    ref_std: Optional[float] = None
    cur_std: Optional[float] = None
    chi2_test: Optional[Dict[str, Any]] = None
    ks_test: Optional[Dict[str, Any]] = None
    ref_top: Optional[Dict[str, Any]] = None
    cur_top: Optional[Dict[str, Any]] = None
    ref_unique: Optional[int] = None
    cur_unique: Optional[int] = None
    detail: Optional[str] = None


class ExplanationResult(BaseModel):
    summary: str
    full_text: str
    used_llm: bool
    model: str


class DriftReportResponse(BaseModel):
    timestamp: str
    overall_severity: str
    features_checked: int
    drifted_count: int
    drifted_features: List[str]
    reference_rows: int
    current_rows: int
    schema: Dict[str, Any]
    features: Dict[str, Any]
    explanation: Optional[ExplanationResult] = None


class FingerprintResponse(BaseModel):
    id: str
    created_at: str
    name: Optional[str]
    num_rows: int
    num_features: int
    features: List[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    explainer_available: bool


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None