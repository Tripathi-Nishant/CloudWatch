"""
Claude API client for DriftWatch.
Wraps the Anthropic SDK with:
  - graceful fallback when no API key is set
  - caching to avoid re-calling for identical reports
  - structured result type
"""

import os
import hashlib
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Explanation:
    summary: str           # one-sentence header
    full_text: str         # DIAGNOSIS / IMPACT / ACTION
    used_llm: bool         # False if fallback was used
    model: str             # which model was called
    feature: Optional[str] # set if this is a per-feature explanation


class ClaudeExplainer:
    """
    Calls Claude API to generate plain-English drift explanations.
    Falls back gracefully to rule-based text if no API key is present.
    """

    MODEL = "claude-haiku-4-5-20251001"   # cheapest + fastest, perfect for this

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._cache: Dict[str, Explanation] = {}
        self._client = None

        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None and bool(self.api_key)

    # ── Public methods ─────────────────────────────────────────────────────────

    def explain_report(self, report: Dict[str, Any]) -> Explanation:
        """Full report explanation — DIAGNOSIS / IMPACT / ACTION."""
        from driftwatch.explainer.prompt_builder import (
            build_explanation_prompt,
            build_summary_prompt
        )

        cache_key = self._hash(report)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.available:
            result = self._fallback_report(report)
            self._cache[cache_key] = result
            return result

        full_prompt    = build_explanation_prompt(report)
        summary_prompt = build_summary_prompt(report)

        full_text = self._call(full_prompt)
        summary   = self._call(summary_prompt)

        result = Explanation(
            summary=summary.strip(),
            full_text=full_text.strip(),
            used_llm=True,
            model=self.MODEL,
            feature=None
        )
        self._cache[cache_key] = result
        return result

    def explain_feature(
        self,
        feature_name: str,
        feature_data: Dict,
        context: Dict = None
    ) -> Explanation:
        """Deep-dive explanation for a single feature."""
        from driftwatch.explainer.prompt_builder import build_feature_prompt

        cache_key = self._hash({"feat": feature_name, "data": feature_data})
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.available:
            result = self._fallback_feature(feature_name, feature_data)
            self._cache[cache_key] = result
            return result

        prompt    = build_feature_prompt(feature_name, feature_data, context)
        full_text = self._call(prompt)

        result = Explanation(
            summary=f"Deep-dive: {feature_name}",
            full_text=full_text.strip(),
            used_llm=True,
            model=self.MODEL,
            feature=feature_name
        )
        self._cache[cache_key] = result
        return result

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call(self, prompt: str) -> str:
        """Single Claude API call. Returns text content."""
        try:
            message = self._client.messages.create(
                model=self.MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            return f"[LLM call failed: {e}]"

    def _hash(self, data: Any) -> str:
        """Cache key from data."""
        return hashlib.md5(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    # ── Rule-based fallbacks (no API key needed) ───────────────────────────────

    def _fallback_report(self, report: Dict[str, Any]) -> Explanation:
        """
        Generate a decent rule-based explanation without any LLM.
        Covers the most common drift patterns so the tool is still
        useful even without an API key.
        """
        sev       = report["overall_severity"]
        drifted   = report.get("drifted_features", [])
        features  = report.get("features", {})
        schema    = report.get("schema", {})
        n_train   = report.get("reference_rows", 0)
        n_serve   = report.get("current_rows", 0)

        # --- Summary ---
        if sev == "stable":
            summary = "All features are stable — no action needed."
        elif sev == "warning":
            summary = f"Early drift detected in {len(drifted)} feature(s): {', '.join(drifted[:3])}."
        else:
            worst = _worst_feature(features)
            summary = f"Critical drift in {worst} and {len(drifted)-1} other feature(s) — model likely degraded."

        # --- Full text ---
        parts = ["DIAGNOSIS"]

        if schema["has_drift"]:
            issues = schema.get("issues", [])
            parts.append(f"  Schema has {len(issues)} issue(s):")
            for iss in issues[:3]:
                parts.append(f"    • {iss['detail']}")

        if drifted:
            parts.append(f"  {len(drifted)} feature(s) show drift: {', '.join(drifted)}")
            for feat in drifted[:3]:
                d = features.get(feat, {})
                if d.get("type") == "numerical":
                    ref_m = d.get("ref_mean")
                    cur_m = d.get("cur_mean")
                    psi   = d.get("psi")
                    if ref_m and cur_m:
                        delta = ((cur_m - ref_m) / abs(ref_m)) * 100
                        parts.append(f"    • {feat}: mean shifted {delta:+.1f}% (PSI={psi})")
                elif d.get("type") == "categorical":
                    p = d.get("chi2_test", {}).get("p_value", "N/A")
                    parts.append(f"    • {feat}: category distribution changed (p={p})")
        else:
            parts.append("  No feature drift detected.")

        parts += [
            "",
            "IMPACT",
            _impact_text(sev, drifted, features),
            "",
            "ACTION",
        ]
        parts += _action_items(sev, drifted, schema, features)

        full_text = "\n".join(parts)

        return Explanation(
            summary=summary,
            full_text=full_text,
            used_llm=False,
            model="rule-based",
            feature=None
        )

    def _fallback_feature(self, name: str, data: Dict) -> Explanation:
        ftype = data.get("type", "unknown")
        fsev  = data.get("severity", "stable")

        if ftype == "numerical":
            ref_m = data.get("ref_mean")
            cur_m = data.get("cur_mean")
            psi   = data.get("psi")
            delta_str = ""
            if ref_m and cur_m and ref_m != 0:
                delta = ((cur_m - ref_m) / abs(ref_m)) * 100
                delta_str = f" The mean shifted {delta:+.1f}% ({ref_m:.2f} → {cur_m:.2f})."
            text = (
                f"{name} has {fsev} numerical drift (PSI={psi}).{delta_str} "
                f"{'Consider investigating the data pipeline for this feature.' if fsev != 'stable' else 'No action needed.'}"
            )
        elif ftype == "categorical":
            p = data.get("chi2_test", {}).get("p_value", "N/A")
            r_top = data.get("ref_top", {})
            c_top = data.get("cur_top", {})
            text = (
                f"{name} has {fsev} categorical drift (chi2 p={p}). "
                f"Training top values: {list(r_top.keys())[:3]}. "
                f"Serving top values: {list(c_top.keys())[:3]}. "
                f"The distribution of categories has shifted significantly."
            )
        else:
            text = f"{name} has a type mismatch between training and serving data. Check your feature pipeline."

        return Explanation(
            summary=f"{name}: {fsev} drift",
            full_text=text,
            used_llm=False,
            model="rule-based",
            feature=name
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _worst_feature(features: Dict) -> str:
    critical = [f for f, d in features.items() if d.get("severity") == "critical"]
    if not critical:
        return list(features.keys())[0] if features else "unknown"
    # Return the one with highest PSI
    return max(
        critical,
        key=lambda f: features[f].get("psi") or 0
    )


def _impact_text(sev: str, drifted: list, features: Dict) -> str:
    if sev == "stable":
        return "  Model performance is likely unaffected."
    elif sev == "warning":
        return (
            f"  Model may show subtle degradation on features: {', '.join(drifted[:3])}. "
            "Predictions may be less accurate for affected segments but the model is still functional."
        )
    else:
        worst = _worst_feature(features)
        d = features.get(worst, {})
        psi = d.get("psi", "")
        return (
            f"  Model performance is likely significantly degraded. "
            f"The worst offender is '{worst}' (PSI={psi}). "
            "Predictions on current serving data are unreliable and should not be trusted for high-stakes decisions."
        )


def _action_items(sev: str, drifted: list, schema: Dict, features: Dict) -> list:
    actions = []
    idx = 1

    if schema.get("has_drift"):
        for iss in schema.get("issues", [])[:2]:
            if iss["issue"] == "missing_column":
                actions.append(f"  {idx}. Fix pipeline: column '{iss['column']}' is missing from serving data.")
                idx += 1
            elif iss["issue"] == "type_change":
                actions.append(f"  {idx}. Fix type mismatch in '{iss['column']}' — check your feature engineering code.")
                idx += 1
            elif iss["issue"] == "null_rate_increase":
                actions.append(f"  {idx}. Investigate null explosion in '{iss['column']}' — upstream data source may be broken.")
                idx += 1

    for feat in drifted[:3]:
        d = features.get(feat, {})
        if d.get("type") == "numerical" and d.get("psi", 0) > 0.5:
            actions.append(f"  {idx}. Retrain with recent data — '{feat}' distribution has shifted dramatically.")
            idx += 1
        elif d.get("type") == "categorical":
            actions.append(f"  {idx}. Review '{feat}' encoding — new categories may be causing prediction errors.")
            idx += 1

    if sev == "critical" and idx == 1:
        actions.append("  1. Retrain the model on recent data immediately.")
        actions.append("  2. Roll back to previous model version while investigating.")

    if not actions:
        actions.append("  1. Continue monitoring. No immediate action required.")

    return actions