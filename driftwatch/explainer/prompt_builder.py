"""
Prompt builder.
Converts a DriftReport into a structured, information-dense prompt for Claude.
The goal: give the LLM exactly what it needs to produce a useful explanation —
not a generic "drift was detected" but a specific, actionable diagnosis.
"""

from typing import Dict, Any


def build_explanation_prompt(report: Dict[str, Any]) -> str:
    """
    Build a full prompt from a drift report dict.
    Includes severity, per-feature stats, schema issues, and mean shifts.
    """
    sev        = report["overall_severity"]
    n_train    = report["reference_rows"]
    n_serve    = report["current_rows"]
    n_drifted  = report["drifted_count"]
    n_total    = report["features_checked"]
    schema     = report["schema"]
    features   = report["features"]

    lines = [
        "You are an ML reliability engineer analysing a training/serving skew report.",
        "Your job: explain what went wrong in plain English, why it matters, and what to do.",
        "Be specific. Use the actual numbers. Do NOT be generic.",
        "Format your response in three clearly labelled sections:",
        "  1. DIAGNOSIS  — what changed and how severely",
        "  2. IMPACT     — how this likely affected model performance",
        "  3. ACTION     — concrete next steps, in priority order",
        "Keep each section to 3–5 sentences. Total response under 300 words.",
        "",
        "=== DRIFT REPORT ===",
        f"Overall severity : {sev.upper()}",
        f"Training rows    : {n_train:,}",
        f"Serving rows     : {n_serve:,}",
        f"Drifted features : {n_drifted} out of {n_total}",
        "",
    ]

    # Schema issues
    if schema["has_drift"]:
        lines.append("--- Schema Issues ---")
        for issue in schema["issues"]:
            lines.append(f"  [{issue['severity'].upper()}] {issue['detail']}")
        lines.append("")

    # Per-feature breakdown
    lines.append("--- Feature-Level Drift ---")
    for feat, data in features.items():
        ftype = data.get("type", "unknown")
        fsev  = data.get("severity", "stable")

        if ftype == "numerical":
            psi      = data.get("psi", "N/A")
            ref_mean = data.get("ref_mean")
            cur_mean = data.get("cur_mean")
            ref_std  = data.get("ref_std")
            cur_std  = data.get("cur_std")

            delta_pct = ""
            if ref_mean and cur_mean and ref_mean != 0:
                delta = ((cur_mean - ref_mean) / abs(ref_mean)) * 100
                delta_pct = f", mean shift {delta:+.1f}%"

            lines.append(
                f"  {feat} [{fsev.upper()}]: type=numerical, PSI={psi}"
                f", train_mean={ref_mean}, serve_mean={cur_mean}"
                f", train_std={ref_std}, serve_std={cur_std}"
                f"{delta_pct}"
            )

        elif ftype == "categorical":
            chi2   = data.get("chi2_test", {})
            p_val  = chi2.get("p_value", "N/A")
            r_top  = data.get("ref_top", {})
            c_top  = data.get("cur_top", {})
            r_uniq = data.get("ref_unique")
            c_uniq = data.get("cur_unique")

            lines.append(
                f"  {feat} [{fsev.upper()}]: type=categorical, chi2_p={p_val}"
                f", train_top={_top3(r_top)}, serve_top={_top3(c_top)}"
                f", train_unique={r_uniq}, serve_unique={c_uniq}"
            )

        elif ftype == "type_mismatch":
            lines.append(f"  {feat} [CRITICAL]: {data.get('detail', 'type mismatch detected')}")

    lines.append("")
    lines.append("=== END REPORT ===")
    lines.append("")
    lines.append("Now write your DIAGNOSIS, IMPACT, and ACTION.")

    return "\n".join(lines)


def build_feature_prompt(feature_name: str, feature_data: Dict, context: Dict = None) -> str:
    """
    Build a focused prompt for a single feature.
    Used when the user asks for a deep-dive on one specific feature.
    """
    ftype = feature_data.get("type", "unknown")
    fsev  = feature_data.get("severity", "stable")

    lines = [
        "You are an ML engineer. Explain this single feature's drift in plain English.",
        "Be specific and actionable. Under 150 words.",
        "Format: one paragraph — what changed, why it matters, what to do.",
        "",
        f"Feature name : {feature_name}",
        f"Severity     : {fsev.upper()}",
        f"Feature type : {ftype}",
        "",
    ]

    if ftype == "numerical":
        lines += [
            f"PSI             : {feature_data.get('psi')}",
            f"KL Divergence   : {feature_data.get('kl_divergence')}",
            f"JS Distance     : {feature_data.get('js_distance')}",
            f"Train mean/std  : {feature_data.get('ref_mean')} / {feature_data.get('ref_std')}",
            f"Serving mean/std: {feature_data.get('cur_mean')} / {feature_data.get('cur_std')}",
        ]
        ks = feature_data.get("ks_test", {})
        if ks:
            lines.append(f"KS test p-value : {ks.get('p_value')} (drifted={ks.get('drifted')})")

    elif ftype == "categorical":
        chi2 = feature_data.get("chi2_test", {})
        lines += [
            f"Chi2 p-value    : {chi2.get('p_value')}",
            f"Train top vals  : {_top3(feature_data.get('ref_top', {}))}",
            f"Serving top vals: {_top3(feature_data.get('cur_top', {}))}",
            f"Train unique    : {feature_data.get('ref_unique')}",
            f"Serving unique  : {feature_data.get('cur_unique')}",
        ]

    if context:
        lines.append(f"\nAdditional context: {context}")

    lines.append("\nExplain this drift now:")
    return "\n".join(lines)


def build_summary_prompt(report: Dict[str, Any]) -> str:
    """
    One-sentence executive summary — for the dashboard header card.
    """
    sev       = report["overall_severity"]
    n_drifted = report["drifted_count"]
    n_total   = report["features_checked"]

    drifted_names = [
        f for f, d in report["features"].items()
        if d.get("severity") in ("warning", "critical")
    ]

    return (
        "You are an ML monitoring system. Write ONE sentence (max 25 words) "
        "summarising this drift report for a dashboard header. "
        "Be direct and specific — mention the worst feature by name.\n\n"
        f"Severity: {sev.upper()}\n"
        f"Drifted: {n_drifted}/{n_total} features\n"
        f"Affected features: {', '.join(drifted_names) if drifted_names else 'none'}\n\n"
        "One sentence summary:"
    )


def _top3(d: dict) -> str:
    """Format top-3 category values for prompt inclusion."""
    items = list(d.items())[:3]
    return "{" + ", ".join(f"{k}:{v}" for k, v in items) + "}"