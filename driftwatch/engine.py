"""
DriftWatch core engine.
Orchestrates schema + statistical checks and produces a unified report.
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, Any, Optional
from datetime import datetime

from driftwatch.detectors.statistical import (
    calculate_psi, calculate_kl_divergence,
    calculate_js_distance, calculate_ks_test,
    calculate_chi_squared, psi_severity
)
from driftwatch.detectors.schema import detect_schema_drift, get_feature_stats


class DriftReport:
    """Full drift analysis result — schema + per-feature statistics."""

    def __init__(self, report: Dict[str, Any]):
        self.raw = report

    @property
    def has_drift(self) -> bool:
        return self.raw["overall_severity"] in ("warning", "critical")

    @property
    def severity(self) -> str:
        return self.raw["overall_severity"]

    @property
    def drifted_features(self) -> list:
        return [
            f for f, data in self.raw["features"].items()
            if data.get("severity") in ("warning", "critical")
        ]

    def to_dict(self) -> Dict:
        return self.raw

    def to_json(self) -> str:
        return json.dumps(self.raw, indent=2, default=str)

    def summary(self) -> str:
        r = self.raw
        lines = [
            f"\n{'='*55}",
            f"  DriftWatch Report — {r['timestamp']}",
            f"{'='*55}",
            f"  Overall Severity : {r['overall_severity'].upper()}",
            f"  Features Checked : {r['features_checked']}",
            f"  Drifted Features : {r['drifted_count']}",
            f"  Schema Issues    : {r['schema']['critical_count']} critical, "
            f"{r['schema']['warning_count']} warning",
            f"{'─'*55}",
        ]
        for feat, data in r["features"].items():
            sev = data.get("severity", "stable")
            icon = "🔴" if sev == "critical" else "🟡" if sev == "warning" else "🟢"
            psi_val = data.get("psi", "N/A")
            lines.append(f"  {icon} {feat:<28} PSI={psi_val}")
        lines.append(f"{'='*55}\n")
        return "\n".join(lines)


class DriftEngine:
    """
    Main engine. Feed it reference (training) and current (serving) DataFrames.
    Get back a full DriftReport.
    """

    def __init__(self, bins: int = 10):
        self.bins = bins

    def analyze(
        self,
        reference: pd.DataFrame,
        current: pd.DataFrame,
        label_column: Optional[str] = None
    ) -> DriftReport:
        """
        Run full drift analysis.
        Optionally exclude label_column from feature drift checks.
        """
        # Drop label column if provided
        ref = reference.drop(columns=[label_column]) if label_column and label_column in reference.columns else reference.copy()
        cur = current.drop(columns=[label_column]) if label_column and label_column in current.columns else current.copy()

        # ── Schema check ──────────────────────────────────────────────────────
        schema_result = detect_schema_drift(ref, cur)

        # ── Per-feature statistical drift ─────────────────────────────────────
        feature_results = {}
        common_cols = list(set(ref.columns) & set(cur.columns))

        for col in common_cols:
            feature_results[col] = self._analyze_feature(ref[col], cur[col])

        # ── Overall severity ──────────────────────────────────────────────────
        drifted = [f for f, d in feature_results.items() if d["severity"] in ("warning", "critical")]
        critical_features = [f for f, d in feature_results.items() if d["severity"] == "critical"]

        if schema_result["overall_severity"] == "critical" or len(critical_features) > 0:
            overall = "critical"
        elif schema_result["overall_severity"] == "warning" or len(drifted) > 0:
            overall = "warning"
        else:
            overall = "stable"

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_severity": overall,
            "features_checked": len(common_cols),
            "drifted_count": len(drifted),
            "drifted_features": drifted,
            "schema": schema_result,
            "features": feature_results,
            "reference_rows": len(reference),
            "current_rows": len(current),
        }

        return DriftReport(report)

    def _analyze_feature(
        self,
        ref_series: pd.Series,
        cur_series: pd.Series
    ) -> Dict[str, Any]:
        """Run the right tests depending on whether the feature is numeric or categorical."""

        is_numeric = pd.api.types.is_numeric_dtype(ref_series)

        if is_numeric:
            psi = calculate_psi(ref_series, cur_series, self.bins)
            kl = calculate_kl_divergence(ref_series, cur_series, self.bins)
            js = calculate_js_distance(ref_series, cur_series, self.bins)
            ks = calculate_ks_test(ref_series, cur_series)
            severity = psi_severity(psi)

            return {
                "type": "numerical",
                "severity": severity,
                "psi": psi,
                "kl_divergence": kl,
                "js_distance": js,
                "ks_test": ks,
                "ref_mean": float(round(ref_series.mean(), 4)) if not ref_series.isnull().all() else None,
                "cur_mean": float(round(cur_series.mean(), 4)) if not cur_series.isnull().all() else None,
                "ref_std": float(round(ref_series.std(), 4)) if not ref_series.isnull().all() else None,
                "cur_std": float(round(cur_series.std(), 4)) if not cur_series.isnull().all() else None,
            }
        else:
            chi2 = calculate_chi_squared(ref_series, cur_series)
            severity = "critical" if chi2["drifted"] and chi2["p_value"] < 0.01 else \
                       "warning" if chi2["drifted"] else "stable"

            return {
                "type": "categorical",
                "severity": severity,
                "chi2_test": chi2,
                "ref_unique": int(ref_series.nunique()),
                "cur_unique": int(cur_series.nunique()),
                "ref_top": ref_series.value_counts().head(3).to_dict(),
                "cur_top": cur_series.value_counts().head(3).to_dict(),
            }