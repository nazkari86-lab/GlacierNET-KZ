#!/usr/bin/env python3
"""Build the current CentralAsia-GlacierBench evidence report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.centralasia_benchmark import build_benchmark_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks/centralasia_glacierbench/current/report.json",
    )
    args = parser.parse_args()
    report = build_benchmark_report(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"{report['benchmark_name']}: "
        f"{report['summary']['model_evaluations_measured']} measured model evaluations, "
        f"{report['summary']['reference_evidence_available']} reference evidence tracks, "
        f"{report['summary']['tracks_data_ready']} data-ready, "
        f"{report['summary']['tracks_blocked']} blocked"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
