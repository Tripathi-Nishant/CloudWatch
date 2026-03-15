#!/usr/bin/env python3
"""
DriftWatch CLI
Usage:
    driftwatch check --training train.csv --serving serving.csv
    driftwatch check --training train.csv --serving serving.csv --label is_fraud
    driftwatch check --training train.csv --serving serving.csv --output report.json
    driftwatch fingerprint --data train.csv --output fingerprint.json
    driftwatch compare --fingerprint fingerprint.json --serving serving.csv
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(
        prog="driftwatch",
        description="Real-time training/serving skew detector for ML pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  driftwatch check --training train.csv --serving serving.csv
  driftwatch check --training train.csv --serving serving.csv --label target --output report.json
  driftwatch fingerprint --data train.csv --output fingerprint.json
  driftwatch compare --fingerprint fingerprint.json --serving serving.csv
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # ── check command ──────────────────────────────────────────────────────────
    check_parser = subparsers.add_parser(
        "check",
        help="Compare training and serving data directly"
    )
    check_parser.add_argument("--training", "-t", required=True, help="Path to training data (CSV or Parquet)")
    check_parser.add_argument("--serving",  "-s", required=True, help="Path to serving data (CSV or Parquet)")
    check_parser.add_argument("--label",    "-l", default=None,  help="Label column to exclude from drift checks")
    check_parser.add_argument("--output",   "-o", default=None,  help="Save full JSON report to this file")
    check_parser.add_argument("--bins",     "-b", default=10, type=int, help="Number of bins for histogram (default: 10)")
    check_parser.add_argument("--quiet",    "-q", action="store_true",  help="Only show drifted features")
    check_parser.add_argument("--json",           action="store_true",  help="Print raw JSON instead of formatted output")
    check_parser.add_argument("--explain",  "-e", action="store_true",  help="Generate LLM explanation")

    # ── fingerprint command ────────────────────────────────────────────────────
    fp_parser = subparsers.add_parser(
        "fingerprint",
        help="Save a statistical fingerprint of your training data"
    )
    fp_parser.add_argument("--data",   "-d", required=True, help="Path to training data")
    fp_parser.add_argument("--output", "-o", required=True, help="Where to save the fingerprint JSON")
    fp_parser.add_argument("--label",  "-l", default=None,  help="Label column to exclude")

    # ── compare command ────────────────────────────────────────────────────────
    cmp_parser = subparsers.add_parser(
        "compare",
        help="Compare serving data against a saved fingerprint"
    )
    cmp_parser.add_argument("--fingerprint", "-f", required=True, help="Path to saved fingerprint JSON")
    cmp_parser.add_argument("--serving",     "-s", required=True, help="Path to serving data")
    cmp_parser.add_argument("--output",      "-o", default=None,  help="Save full JSON report to this file")
    cmp_parser.add_argument("--quiet",       "-q", action="store_true")
    cmp_parser.add_argument("--json",              action="store_true")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "check":
        from driftwatch.cli.commands import cmd_check
        cmd_check(args)

    elif args.command == "fingerprint":
        from driftwatch.cli.commands import cmd_fingerprint
        cmd_fingerprint(args)

    elif args.command == "compare":
        from driftwatch.cli.commands import cmd_compare
        cmd_compare(args)


if __name__ == "__main__":
    main()
