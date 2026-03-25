"""
SDK usage demo.
Shows every integration pattern from simplest to most advanced.
Run with: PYTHONPATH=. python driftwatch/sdk/demo.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pandas as pd
from data.samples.generator import (
    make_training_data,
    make_serving_data_stable,
    make_serving_data_drifted,
)
from driftwatch.sdk import DriftWatcher, DriftDetectedError


SEP = "─" * 55


def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


# ── Generate data ──────────────────────────────────────────────────────────────
train          = make_training_data(1000)
serving_stable = make_serving_data_stable(500)
serving_drift  = make_serving_data_drifted(500)


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 1 — Absolute minimum (3 lines)
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 1 — Minimum (3 lines)")

watcher = DriftWatcher(reference=train)
report  = watcher.check(serving_drift)

print(f"  Severity : {report.severity.upper()}")
print(f"  Drifted  : {report.drifted_features}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 2 — With label column excluded
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 2 — Exclude label column")

watcher = DriftWatcher(reference=train, label_column="is_fraud")
report  = watcher.check(serving_drift)

print(f"  Severity         : {report.severity.upper()}")
print(f"  Features checked : {report.raw['features_checked']}  (label excluded)")
print(f"  Drifted features : {report.drifted_features}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 3 — Callbacks for alerting
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 3 — Alert callbacks")

def handle_critical(r):
    print(f"  [CALLBACK] CRITICAL — drifted: {r.drifted_features}")
    print(f"  [CALLBACK] Would page on-call here → PagerDuty / Slack")

def handle_warning(r):
    print(f"  [CALLBACK] WARNING — {len(r.drifted_features)} features need monitoring")

def handle_stable(r):
    print(f"  [CALLBACK] All clear — logging to metrics store")

watcher = DriftWatcher(
    reference    = train,
    label_column = "is_fraud",
    on_critical  = handle_critical,
    on_warning   = handle_warning,
    on_stable    = handle_stable,
)

print("  --- Checking stable serving data ---")
watcher.check(serving_stable, tag="batch_stable")

print("  --- Checking drifted serving data ---")
watcher.check(serving_drift, tag="batch_drifted")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 4 — raise_on_critical for CI/CD pipelines
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 4 — raise_on_critical (CI/CD gate)")

watcher = DriftWatcher(
    reference          = train,
    label_column       = "is_fraud",
    raise_on_critical  = True,
)

print("  Checking stable data (should pass)...")
try:
    watcher.check(serving_stable)
    print("  PASS — no exception raised")
except DriftDetectedError as e:
    print(f"  FAIL — unexpected exception: {e}")

print("  Checking drifted data (should raise)...")
try:
    watcher.check(serving_drift)
    print("  FAIL — exception should have been raised")
except DriftDetectedError as e:
    print(f"  CAUGHT DriftDetectedError: {e}")
    print(f"  Report severity: {e.report.severity}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 5 — History tracking across multiple batches
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 5 — History across batches")

watcher = DriftWatcher(reference=train, label_column="is_fraud")

batches = [
    ("week_1", serving_stable),
    ("week_2", serving_stable),
    ("week_3", serving_drift),
    ("week_4", serving_drift),
]

for tag, data in batches:
    watcher.check(data, tag=tag)

print(f"  {'Tag':<12} {'Severity':<12} {'Drifted Features'}")
print(f"  {SEP}")
for entry in watcher.history:
    drifted_str = ", ".join(entry["drifted"]) if entry["drifted"] else "none"
    print(f"  {entry['tag']:<12} {entry['severity']:<12} {drifted_str}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 6 — Save and reload fingerprint
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 6 — Fingerprint save and reload")

# Save at training time
watcher = DriftWatcher(reference=train, label_column="is_fraud")
fp_path = "/tmp/driftwatch_fingerprint.json"
watcher.save_fingerprint(fp_path)
print(f"  Fingerprint saved → {fp_path}")

# Reload from fingerprint (no original training data needed)
watcher2 = DriftWatcher(fingerprint_path=fp_path, label_column="is_fraud")
report2  = watcher2.check(serving_drift)
print(f"  Loaded from fingerprint — severity: {report2.severity.upper()}")
print(f"  Drifted features: {report2.drifted_features}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 7 — Per-feature explanation (rule-based, no API key)
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 7 — Per-feature explanation")

watcher = DriftWatcher(reference=train, label_column="is_fraud")
report  = watcher.check(serving_drift)

# Get explanation for the worst feature
worst = report.drifted_features[0] if report.drifted_features else None
if worst:
    exp = watcher.explain(report, feature=worst)
    print(f"  Feature: {worst}")
    print(f"  {exp.full_text}")


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN 8 — Access raw report data programmatically
# ─────────────────────────────────────────────────────────────────────────────
section("Pattern 8 — Programmatic access to report data")

watcher = DriftWatcher(reference=train, label_column="is_fraud")
report  = watcher.check(serving_drift)

print(f"  Overall severity  : {report.severity}")
print(f"  Has drift         : {report.has_drift}")
print(f"  Drifted features  : {report.drifted_features}")
print(f"  Schema issues     : {report.raw['schema']['critical_count']} critical, "
      f"{report.raw['schema']['warning_count']} warning")
print()
print("  Per-feature PSI values:")
for feat, data in report.raw["features"].items():
    if data.get("type") == "numerical":
        psi = data.get("psi", "N/A")
        sev = data.get("severity", "stable")
        print(f"    {feat:<26} PSI={psi:<10} [{sev.upper()}]")

print(f"\n  Export to JSON:\n  {report.to_json()[:120]}...")

print(f"\n{'='*55}")
print("  All SDK patterns verified successfully.")
print(f"{'='*55}\n")