"""
Terminal renderer for DriftWatch reports.
Clean, coloured, readable output without any external dependencies.
"""

from typing import Dict, Any


# ANSI color codes — degrade gracefully if terminal doesn't support them
class C:
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"


def severity_color(sev: str) -> str:
    return {
        "critical": C.RED,
        "warning":  C.YELLOW,
        "stable":   C.GREEN,
    }.get(sev, C.WHITE)


def severity_icon(sev: str) -> str:
    return {
        "critical": "CRIT",
        "warning":  "WARN",
        "stable":   "OK  ",
    }.get(sev, "????")


def render_report(report, quiet: bool = False):
    r = report.raw
    sev = r["overall_severity"]
    col = severity_color(sev)

    print()
    print(f"  {C.BOLD}{'─'*54}{C.RESET}")
    print(f"  {C.BOLD}DriftWatch Report{C.RESET}  {C.DIM}{r['timestamp']}{C.RESET}")
    print(f"  {'─'*54}")
    print(f"  Overall Status   {col}{C.BOLD}{sev.upper()}{C.RESET}")
    print(f"  Features Checked {r['features_checked']}")
    print(f"  Drifted Features {_drift_count_str(r['drifted_count'], r['features_checked'])}")
    print(f"  Rows             {r['reference_rows']:,} train  /  {r['current_rows']:,} serving")
    print(f"  {'─'*54}")

    # Schema issues
    schema = r["schema"]
    if schema["has_drift"]:
        print(f"\n  {C.BOLD}Schema Issues{C.RESET}")
        for issue in schema["issues"]:
            ic = severity_color(issue["severity"])
            print(f"  {ic}[{severity_icon(issue['severity'])}]{C.RESET}  {issue['detail']}")
    else:
        print(f"\n  {C.GREEN}Schema{C.RESET}  No issues detected")

    # Feature drift table
    print(f"\n  {C.BOLD}Feature Drift{C.RESET}")
    print(f"  {'Feature':<26} {'Type':<12} {'PSI / Test':<14} {'Status'}")
    print(f"  {'─'*26} {'─'*12} {'─'*14} {'─'*10}")

    for feat, data in r["features"].items():
        sev_f = data.get("severity", "stable")

        if quiet and sev_f == "stable":
            continue

        col_f = severity_color(sev_f)
        icon  = severity_icon(sev_f)
        ftype = data.get("type", "unknown")

        if ftype == "numerical":
            metric = f"PSI={data.get('psi', 'N/A')}"
        elif ftype == "categorical":
            p = data.get("chi2_test", {}).get("p_value", "N/A")
            metric = f"p={p}"
        else:
            metric = "type mismatch"

        print(
            f"  {feat:<26} "
            f"{C.DIM}{ftype:<12}{C.RESET} "
            f"{metric:<14} "
            f"{col_f}[{icon}]{C.RESET}"
        )

    # Mean shift summary for drifted numerical features
    drifted_num = {
        f: d for f, d in r["features"].items()
        if d.get("type") == "numerical" and d.get("severity") in ("warning", "critical")
    }
    if drifted_num:
        print(f"\n  {C.BOLD}Mean Shift (drifted features){C.RESET}")
        print(f"  {'Feature':<26} {'Train Mean':>12}  {'Serve Mean':>12}  {'Delta':>10}")
        print(f"  {'─'*26} {'─'*12}  {'─'*12}  {'─'*10}")
        for feat, data in drifted_num.items():
            ref_mean = data.get("ref_mean")
            cur_mean = data.get("cur_mean")
            if ref_mean is not None and cur_mean is not None:
                delta = cur_mean - ref_mean
                delta_pct = (delta / ref_mean * 100) if ref_mean != 0 else 0
                col_d = C.RED if abs(delta_pct) > 20 else C.YELLOW
                print(
                    f"  {feat:<26} "
                    f"{ref_mean:>12.2f}  "
                    f"{cur_mean:>12.2f}  "
                    f"{col_d}{delta_pct:>+9.1f}%{C.RESET}"
                )

    # Final verdict
    print(f"\n  {'─'*54}")
    if sev == "stable":
        print(f"  {C.GREEN}{C.BOLD}All clear.{C.RESET} No significant drift detected.")
    elif sev == "warning":
        print(f"  {C.YELLOW}{C.BOLD}Monitor.{C.RESET} Some features show early drift signs.")
        print(f"  {C.DIM}Consider retraining if drift worsens.{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}Action required.{C.RESET} Significant drift detected.")
        print(f"  {C.DIM}Model performance is likely degraded. Retrain recommended.{C.RESET}")
    print(f"  {'─'*54}\n")


def render_fingerprint_saved(fingerprint: Dict[str, Any]):
    print(f"\n  {C.GREEN}Fingerprint saved{C.RESET}")
    print(f"  {'─'*40}")
    print(f"  Features : {fingerprint['num_features']}")
    print(f"  Rows     : {fingerprint['num_rows']:,}")
    print(f"  Features : {', '.join(fingerprint['features'][:6])}"
          f"{'...' if len(fingerprint['features']) > 6 else ''}")
    print(f"\n  Use with:")
    print(f"  {C.CYAN}driftwatch compare --fingerprint <file> --serving serving.csv{C.RESET}\n")


def _drift_count_str(drifted: int, total: int) -> str:
    if drifted == 0:
        return f"{C.GREEN}{drifted} / {total}{C.RESET}"
    elif drifted <= total // 3:
        return f"{C.YELLOW}{drifted} / {total}{C.RESET}"
    else:
        return f"{C.RED}{drifted} / {total}{C.RESET}"