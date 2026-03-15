"""
DriftWatch Python SDK.

Minimal usage (3 lines):
    from driftwatch.sdk import DriftWatcher
    watcher = DriftWatcher(reference=train_df)
    report  = watcher.check(serving_df)

Full usage with callbacks:
    watcher = DriftWatcher(
        reference     = train_df,
        label_column  = "target",
        on_critical   = lambda r: alert_team(r),
        on_warning    = lambda r: log_warning(r),
        explain       = True,
        api_key       = "sk-ant-..."
    )
    report = watcher.check(serving_df)
    if report.has_drift:
        print(report.explanation.full_text)
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Union
from datetime import datetime

from driftwatch.engine import DriftEngine, DriftReport
from driftwatch.detectors.schema import get_feature_stats


class DriftWatcher:
    """
    The main SDK class.
    Instantiate once with your training data (or a saved fingerprint path).
    Call .check() every time you want to compare serving data against it.
    """

    def __init__(
        self,
        reference: Optional[pd.DataFrame] = None,
        fingerprint_path: Optional[str] = None,
        label_column: Optional[str] = None,
        bins: int = 10,
        explain: bool = False,
        api_key: Optional[str] = None,
        on_critical: Optional[Callable[[DriftReport], None]] = None,
        on_warning:  Optional[Callable[[DriftReport], None]] = None,
        on_stable:   Optional[Callable[[DriftReport], None]] = None,
        raise_on_critical: bool = False,
    ):
        """
        Args:
            reference:         Training DataFrame. Provide this OR fingerprint_path.
            fingerprint_path:  Path to a saved .json fingerprint file.
            label_column:      Column to exclude from drift checks (your target/label).
            bins:              Number of histogram bins for PSI calculation.
            explain:           If True, generate LLM explanation on every check().
            api_key:           Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            on_critical:       Callback fired when severity == 'critical'.
            on_warning:        Callback fired when severity == 'warning'.
            on_stable:         Callback fired when severity == 'stable'.
            raise_on_critical: If True, raise DriftDetectedError on critical severity.
        """
        if reference is None and fingerprint_path is None:
            raise ValueError("Provide either reference DataFrame or fingerprint_path.")

        self._engine       = DriftEngine(bins=bins)
        self._label_column = label_column
        self._explain      = explain
        self._api_key      = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._on_critical  = on_critical
        self._on_warning   = on_warning
        self._on_stable    = on_stable
        self._raise        = raise_on_critical
        self._history: list[dict] = []

        # Set up reference
        if reference is not None:
            self._reference = reference
            self._fingerprint = None
        else:
            self._reference, self._fingerprint = self._load_fingerprint(fingerprint_path)

        # Lazy-load explainer only if needed
        self._explainer = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(
        self,
        serving: pd.DataFrame,
        tag: Optional[str] = None,
    ) -> DriftReport:
        """
        Compare serving data against the reference.

        Args:
            serving: DataFrame of current/serving data.
            tag:     Optional label for this check (e.g. "2024-W12", "batch_42").

        Returns:
            DriftReport with full analysis results.
        """
        report = self._engine.analyze(
            self._reference,
            serving,
            label_column=self._label_column
        )

        # Attach explanation if requested
        if self._explain:
            exp = self._get_explainer().explain_report(report.raw)
            report.raw["explanation"] = {
                "summary":   exp.summary,
                "full_text": exp.full_text,
                "used_llm":  exp.used_llm,
                "model":     exp.model,
            }

        # Record in history
        entry = {
            "timestamp": report.raw["timestamp"],
            "tag":       tag,
            "severity":  report.severity,
            "drifted":   report.drifted_features,
        }
        self._history.append(entry)

        # Fire callbacks
        if report.severity == "critical":
            if self._on_critical:
                self._on_critical(report)
            if self._raise:
                raise DriftDetectedError(report)

        elif report.severity == "warning":
            if self._on_warning:
                self._on_warning(report)

        else:
            if self._on_stable:
                self._on_stable(report)

        return report

    def explain(self, report: DriftReport, feature: Optional[str] = None):
        """
        Generate an explanation for an existing report.
        Useful if you didn't pass explain=True at init time.
        """
        explainer = self._get_explainer()
        if feature:
            feat_data = report.raw["features"].get(feature)
            if not feat_data:
                raise ValueError(f"Feature '{feature}' not found in report.")
            return explainer.explain_feature(feature, feat_data)
        return explainer.explain_report(report.raw)

    def save_fingerprint(self, path: str):
        """
        Save the reference DataFrame as a fingerprint JSON.
        Use later to reconstruct a DriftWatcher without needing the original data.
        """
        df = self._reference
        if self._label_column and self._label_column in df.columns:
            df = df.drop(columns=[self._label_column])

        fingerprint = {
            "created_at":   datetime.utcnow().isoformat(),
            "num_rows":     len(df),
            "num_features": len(df.columns),
            "features":     list(df.columns),
            "stats":        get_feature_stats(df),
        }
        with open(path, "w") as f:
            json.dump(fingerprint, f, indent=2, default=str)
        return path

    @property
    def history(self) -> list:
        """List of all past check() results — severity + drifted features."""
        return self._history

    @property
    def last_report(self) -> Optional[dict]:
        """Most recent check summary."""
        return self._history[-1] if self._history else None

    # ── Internal ───────────────────────────────────────────────────────────────

    def _get_explainer(self):
        if self._explainer is None:
            from driftwatch.explainer.claude_client import ClaudeExplainer
            self._explainer = ClaudeExplainer(api_key=self._api_key)
        return self._explainer

    def _load_fingerprint(self, path: str):
        """Reconstruct a synthetic reference DataFrame from a fingerprint file."""
        with open(path) as f:
            fp = json.load(f)

        n = min(fp["num_rows"], 2000)
        ref_data = {}

        for feat, stat in fp["stats"].items():
            dtype = stat["dtype"]
            if dtype.startswith("float") or dtype.startswith("int"):
                mean = stat.get("mean") or 0
                std  = stat.get("std") or 1
                col  = np.random.normal(mean, std, n)
                if dtype.startswith("int"):
                    col = col.astype(int)
                ref_data[feat] = col
            else:
                top = stat.get("top_values", {})
                if top:
                    cats   = list(top.keys())
                    counts = list(top.values())
                    total  = sum(counts)
                    probs  = [c / total for c in counts]
                    ref_data[feat] = np.random.choice(cats, n, p=probs)
                else:
                    ref_data[feat] = ["unknown"] * n

        return pd.DataFrame(ref_data), fp


class DriftDetectedError(Exception):
    """
    Raised when severity == 'critical' and raise_on_critical=True.
    Carries the full DriftReport so callers can inspect it.
    """
    def __init__(self, report: DriftReport):
        self.report = report
        super().__init__(
            f"Critical drift detected in: {', '.join(report.drifted_features)}"
        )