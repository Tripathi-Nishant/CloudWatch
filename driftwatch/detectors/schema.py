"""
Schema drift detector.
Catches missing columns, type changes, null rate explosions — before stats even matter.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any


def detect_schema_drift(
    reference: pd.DataFrame,
    current: pd.DataFrame
) -> Dict[str, Any]:
    """
    Compare schema between training and serving data.
    Returns a full diff report with severity per issue.
    """
    issues = []
    ref_cols = set(reference.columns)
    cur_cols = set(current.columns)

    # ── Missing columns (training had them, serving doesn't) ──────────────────
    missing = ref_cols - cur_cols
    for col in missing:
        issues.append({
            "column": col,
            "issue": "missing_column",
            "severity": "critical",
            "detail": f"Column '{col}' exists in training but is absent in serving data."
        })

    # ── New columns (serving has extras training didn't) ──────────────────────
    extra = cur_cols - ref_cols
    for col in extra:
        issues.append({
            "column": col,
            "issue": "extra_column",
            "severity": "warning",
            "detail": f"Column '{col}' appeared in serving data but was not in training."
        })

    # ── Type changes ──────────────────────────────────────────────────────────
    common_cols = ref_cols & cur_cols
    for col in common_cols:
        ref_dtype = str(reference[col].dtype)
        cur_dtype = str(current[col].dtype)
        if ref_dtype != cur_dtype:
            issues.append({
                "column": col,
                "issue": "type_change",
                "severity": "critical",
                "detail": f"Column '{col}' changed type: {ref_dtype} → {cur_dtype}"
            })

    # ── Null rate explosion ───────────────────────────────────────────────────
    for col in common_cols:
        ref_null_rate = reference[col].isnull().mean()
        cur_null_rate = current[col].isnull().mean()
        delta = cur_null_rate - ref_null_rate

        if delta > 0.20:
            issues.append({
                "column": col,
                "issue": "null_rate_increase",
                "severity": "critical" if delta > 0.40 else "warning",
                "detail": (
                    f"Null rate in '{col}' increased by {delta:.1%}: "
                    f"{ref_null_rate:.1%} (train) → {cur_null_rate:.1%} (serving)"
                )
            })

    # ── Unique value collapse (categorical columns) ───────────────────────────
    for col in common_cols:
        if reference[col].dtype == object or str(reference[col].dtype) == "category":
            ref_unique = set(str(x) for x in reference[col].dropna().unique())
            cur_unique = set(str(x) for x in current[col].dropna().unique())
            unseen = cur_unique - ref_unique
            if unseen:
                issues.append({
                    "column": col,
                    "issue": "unseen_categories",
                    "severity": "warning",
                    "detail": (
                        f"Column '{col}' has {len(unseen)} unseen categories in serving: "
                        f"{list(unseen)[:5]}{'...' if len(unseen) > 5 else ''}"
                    )
                })

    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    return {
        "has_drift": len(issues) > 0,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "overall_severity": (
            "critical" if critical_count > 0
            else "warning" if warning_count > 0
            else "stable"
        ),
        "issues": issues
    }


def get_feature_stats(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Compute a per-column stats fingerprint.
    Saved at training time, compared at serving time.
    """
    stats = {}
    for col in df.columns:
        col_stats = {
            "dtype": str(df[col].dtype),
            "null_rate": float(df[col].isnull().mean()),
            "unique_count": int(df[col].nunique()),
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            col_stats.update({
                "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                "std": float(df[col].std()) if not df[col].isnull().all() else None,
                "min": float(df[col].min()) if not df[col].isnull().all() else None,
                "max": float(df[col].max()) if not df[col].isnull().all() else None,
                "p25": float(df[col].quantile(0.25)) if not df[col].isnull().all() else None,
                "p50": float(df[col].quantile(0.50)) if not df[col].isnull().all() else None,
                "p75": float(df[col].quantile(0.75)) if not df[col].isnull().all() else None,
            })
        else:
            top_values = df[col].value_counts().head(10).to_dict()
            col_stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}

        stats[col] = col_stats
    return stats