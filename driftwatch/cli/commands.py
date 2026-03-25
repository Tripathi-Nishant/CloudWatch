"""
CLI command implementations — check, fingerprint, compare.
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from driftwatch.engine import DriftEngine
from driftwatch.detectors.schema import get_feature_stats
from driftwatch.cli.renderer import render_report, render_fingerprint_saved


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_data(path: str) -> pd.DataFrame:
    """Load CSV or Parquet. Exit with clear message if file not found."""
    if not os.path.exists(path):
        _error(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".parquet":
            return pd.read_parquet(path)
        elif ext in (".csv", ".tsv"):
            sep = "\t" if ext == ".tsv" else ","
            return pd.read_csv(path, sep=sep)
        else:
            # Try CSV as fallback
            return pd.read_csv(path)
    except Exception as e:
        _error(f"Could not read {path}: {e}")


def save_json(data: dict, path: str):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    _success(f"Report saved → {path}")


def _error(msg: str):
    print(f"\n  ERROR  {msg}\n", file=sys.stderr)
    sys.exit(1)


def _success(msg: str):
    print(f"  ✓  {msg}")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_check(args):
    """
    driftwatch check --training train.csv --serving serving.csv
    Direct comparison between two files.
    """
    print(f"\n  DriftWatch  v0.1.0")
    print(f"  {'─'*40}")
    print(f"  Loading training data  → {args.training}")
    training = load_data(args.training)
    print(f"  Loading serving data   → {args.serving}")
    serving = load_data(args.serving)

    print(f"\n  Running analysis  ({len(training)} train rows, {len(serving)} serving rows)...")

    engine = DriftEngine(bins=args.bins)
    report = engine.analyze(training, serving, label_column=args.label)

    if args.json:
        print(report.to_json())
    else:
        render_report(report, quiet=args.quiet)

    if args.output:
        save_json(report.to_dict(), args.output)

    # Exit code 1 if critical drift — useful for CI pipelines
    if report.severity == "critical":
        sys.exit(1)
    elif report.severity == "warning":
        sys.exit(2)
    else:
        sys.exit(0)


def cmd_fingerprint(args):
    """
    driftwatch fingerprint --data train.csv --output fingerprint.json
    Save a statistical fingerprint at training time.
    Use later with `driftwatch compare` without needing the original training data.
    """
    print(f"\n  DriftWatch  — Fingerprint Mode")
    print(f"  {'─'*40}")
    print(f"  Loading data  → {args.data}")
    df = load_data(args.data)

    if args.label and args.label in df.columns:
        df = df.drop(columns=[args.label])

    print(f"  Computing fingerprint for {len(df.columns)} features...")
    stats = get_feature_stats(df)

    fingerprint = {
        "created_at": datetime.utcnow().isoformat(),
        "source_file": args.data,
        "num_rows": len(df),
        "num_features": len(df.columns),
        "features": list(df.columns),
        "stats": stats
    }

    save_json(fingerprint, args.output)
    render_fingerprint_saved(fingerprint)


def cmd_compare(args):
    """
    driftwatch compare --fingerprint fingerprint.json --serving serving.csv
    Compare serving data against a saved training fingerprint.
    Reconstructs a reference DataFrame from fingerprint stats for comparison.
    """
    print(f"\n  DriftWatch  — Compare Mode")
    print(f"  {'─'*40}")

    if not os.path.exists(args.fingerprint):
        _error(f"Fingerprint file not found: {args.fingerprint}")

    with open(args.fingerprint) as f:
        fingerprint = json.load(f)

    print(f"  Fingerprint  → {fingerprint['num_features']} features, {fingerprint['num_rows']} rows")
    print(f"  Created at   → {fingerprint['created_at']}")
    print(f"  Loading serving data → {args.serving}")

    serving = load_data(args.serving)

    # Reconstruct a synthetic reference DataFrame from fingerprint stats
    import numpy as np
    n = min(fingerprint["num_rows"], 1000)
    ref_data = {}

    for feat, stat in fingerprint["stats"].items():
        if stat["dtype"].startswith("float") or stat["dtype"].startswith("int"):
            mean = stat.get("mean") or 0
            std  = stat.get("std")  or 1
            col  = np.random.normal(mean, std, n)
            if stat["dtype"].startswith("int"):
                col = col.astype(int)
            ref_data[feat] = col
        else:
            top = stat.get("top_values", {})
            if top:
                categories = list(top.keys())
                counts = list(top.values())
                total = sum(counts)
                probs = [c / total for c in counts]
                ref_data[feat] = np.random.choice(categories, n, p=probs)
            else:
                ref_data[feat] = ["unknown"] * n

    reference = pd.DataFrame(ref_data)

    print(f"\n  Running analysis  ({n} ref rows, {len(serving)} serving rows)...")

    engine = DriftEngine()
    report = engine.analyze(reference, serving)

    if args.json:
        print(report.to_json())
    else:
        render_report(report, quiet=args.quiet)

    if args.output:
        save_json(report.to_dict(), args.output)

    if report.severity == "critical":
        sys.exit(1)
    elif report.severity == "warning":
        sys.exit(2)
    else:
        sys.exit(0)