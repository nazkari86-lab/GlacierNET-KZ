#!/usr/bin/env python3
"""Rebuild the decision-facing evidence package from current local artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
SUMMARY = ROOT / "results" / "decision_readiness_summary.json"


def run_step(label: str, script: str) -> None:
    print(f"\n== {label} ==", flush=True)
    subprocess.run([PYTHON, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)


def main() -> int:
    steps = [
        ("Validate local GeoTIFF quality", "validate_data_quality.py"),
        ("Refresh raster inventory", "build_data_inventory.py"),
        ("Refresh decision readiness tables", "build_decision_readiness_tables.py"),
    ]
    for label, script in steps:
        run_step(label, script)

    if not SUMMARY.exists():
        raise FileNotFoundError(f"Expected summary was not created: {SUMMARY}")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    trend = summary.get("strict_trend", {})
    print("\n== Project evidence package summary ==", flush=True)
    print(f"strict_trend_ok={trend.get('ok')}", flush=True)
    print(f"n_years={trend.get('n_years')}", flush=True)
    print(f"slope_km2_per_year={trend.get('slope_km2_per_year')}", flush=True)
    print(f"p_value={trend.get('p_value')}", flush=True)
    print(f"forecast_2050_km2={trend.get('forecast_2050_km2')}", flush=True)
    print(f"summary={SUMMARY.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
