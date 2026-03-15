"""
Core statistical drift detectors.
PSI, KL Divergence, Jensen-Shannon Distance — all in one place.
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency, ks_2samp
from typing import Dict, Any


# ─── PSI ──────────────────────────────────────────────────────────────────────

def calculate_psi(
    reference: pd.Series,
    current: pd.Series,
    bins: int = 10
) -> float:
    """
    Population Stability Index.
    Industry standard for detecting distribution shift in numerical features.

    Interpretation:
        PSI < 0.10  → No significant shift (green)
        PSI < 0.20  → Moderate shift — monitor (yellow)
        PSI >= 0.20 → Significant shift — action needed (red)
    """
    reference = reference.dropna()
    current = current.dropna()

    if len(reference) == 0 or len(current) == 0:
        return 0.0

    # Build bins from reference distribution
    breakpoints = np.linspace(
        min(reference.min(), current.min()),
        max(reference.max(), current.max()),
        bins + 1
    )

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cur_counts, _ = np.histogram(current, bins=breakpoints)

    # Convert to proportions, avoid division by zero
    ref_pct = ref_counts / len(reference)
    cur_pct = cur_counts / len(current)

    # Replace zeros to avoid log(0)
    ref_pct = np.where(ref_pct == 0, 1e-6, ref_pct)
    cur_pct = np.where(cur_pct == 0, 1e-6, cur_pct)

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(round(psi, 6))


def psi_severity(psi: float) -> str:
    if psi < 0.10:
        return "stable"
    elif psi < 0.20:
        return "warning"
    else:
        return "critical"


# ─── KL DIVERGENCE ────────────────────────────────────────────────────────────

def calculate_kl_divergence(
    reference: pd.Series,
    current: pd.Series,
    bins: int = 10
) -> float:
    """
    KL Divergence (Kullback-Leibler).
    Measures how much information is lost when using reference to approximate current.
    NOT symmetric — direction matters.

    Interpretation:
        KL = 0      → Identical distributions
        KL < 0.1    → Minor drift
        KL >= 0.1   → Notable drift
    """
    reference = reference.dropna()
    current = current.dropna()

    if len(reference) == 0 or len(current) == 0:
        return 0.0

    breakpoints = np.linspace(
        min(reference.min(), current.min()),
        max(reference.max(), current.max()),
        bins + 1
    )

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cur_counts, _ = np.histogram(current, bins=breakpoints)

    ref_pct = ref_counts / len(reference)
    cur_pct = cur_counts / len(current)

    ref_pct = np.where(ref_pct == 0, 1e-6, ref_pct)
    cur_pct = np.where(cur_pct == 0, 1e-6, cur_pct)

    kl = np.sum(cur_pct * np.log(cur_pct / ref_pct))
    return float(round(kl, 6))


# ─── JENSEN-SHANNON DISTANCE ──────────────────────────────────────────────────

def calculate_js_distance(
    reference: pd.Series,
    current: pd.Series,
    bins: int = 10
) -> float:
    """
    Jensen-Shannon Distance.
    Symmetric, bounded [0, 1] version of KL — better for dashboards.

    Interpretation:
        JS = 0.0    → Identical distributions
        JS < 0.1    → Stable
        JS < 0.2    → Warning
        JS >= 0.2   → Critical drift
    """
    reference = reference.dropna()
    current = current.dropna()

    if len(reference) == 0 or len(current) == 0:
        return 0.0

    breakpoints = np.linspace(
        min(reference.min(), current.min()),
        max(reference.max(), current.max()),
        bins + 1
    )

    ref_counts, _ = np.histogram(reference, bins=breakpoints)
    cur_counts, _ = np.histogram(current, bins=breakpoints)

    ref_pct = (ref_counts / len(reference)).astype(float)
    cur_pct = (cur_counts / len(current)).astype(float)

    ref_pct = np.where(ref_pct == 0, 1e-6, ref_pct)
    cur_pct = np.where(cur_pct == 0, 1e-6, cur_pct)

    js = jensenshannon(ref_pct, cur_pct)
    return float(round(js, 6))


# ─── KS TEST (for numerical) ──────────────────────────────────────────────────

def calculate_ks_test(
    reference: pd.Series,
    current: pd.Series
) -> Dict[str, Any]:
    """
    Kolmogorov-Smirnov test.
    Non-parametric — doesn't assume any distribution shape.
    Returns statistic and p-value.

    p-value < 0.05 → distributions are statistically different
    """
    reference = reference.dropna()
    current = current.dropna()

    if len(reference) == 0 or len(current) == 0:
        return {"statistic": 0.0, "p_value": 1.0, "drifted": False}

    stat, p_value = ks_2samp(reference, current)
    return {
        "statistic": float(round(stat, 6)),
        "p_value": float(round(p_value, 6)),
        "drifted": bool(p_value < 0.05)
    }


# ─── CHI-SQUARED (for categorical) ────────────────────────────────────────────

def calculate_chi_squared(
    reference: pd.Series,
    current: pd.Series
) -> Dict[str, Any]:
    """
    Chi-squared test for categorical feature drift.
    Compares value frequency distributions between reference and current.

    p-value < 0.05 → category distribution has shifted
    """
    reference = reference.dropna().astype(str)
    current = current.dropna().astype(str)

    if len(reference) == 0 or len(current) == 0:
        return {"statistic": 0.0, "p_value": 1.0, "drifted": False}

    all_categories = set(reference.unique()) | set(current.unique())

    ref_counts = reference.value_counts()
    cur_counts = current.value_counts()

    ref_freq = [ref_counts.get(cat, 0) for cat in all_categories]
    cur_freq = [cur_counts.get(cat, 0) for cat in all_categories]

    contingency = np.array([ref_freq, cur_freq])

    # Need at least 2 categories and non-zero counts
    if contingency.shape[1] < 2 or contingency.sum() == 0:
        return {"statistic": 0.0, "p_value": 1.0, "drifted": False}

    try:
        stat, p_value, _, _ = chi2_contingency(contingency)
        return {
            "statistic": float(round(stat, 6)),
            "p_value": float(round(p_value, 6)),
            "drifted": bool(p_value < 0.05)
        }
    except Exception:
        return {"statistic": 0.0, "p_value": 1.0, "drifted": False}