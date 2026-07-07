#!/usr/bin/env python3
"""Fail if predictions reference years without raw source files (data integrity gate)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config


def main() -> int:
    errors: list[str] = []
    pred_dir = ROOT / "predictions"

    for year_dir in sorted(pred_dir.iterdir()) if pred_dir.exists() else []:
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        s2 = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
        ls = config.DATA_RAW_LANDSAT / f"landsat_{year}.tif"
        if not s2.exists() and not ls.exists():
            errors.append(f"predictions/{year} exists but no raw sentinel2_{year}.tif or landsat_{year}.tif")

        for tif in (s2, ls):
            if tif.exists() and tif.stat().st_size < 1_000_000:
                errors.append(f"{tif.name} is too small ({tif.stat().st_size} bytes) — likely incomplete download")

    status_path = config.RESULTS_DIR / "pipeline_status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        for year in status.get("missing_sentinel2", []):
            if (config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif").exists():
                errors.append(f"pipeline_status.json lists missing_sentinel2={year} but file exists — run pipeline_status.py")

    areas_csv = config.TABLES_DIR / "glacier_areas_all_years.csv"
    if areas_csv.exists():
        import csv

        with areas_csv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                y = int(row["year"])
                if not (config.DATA_RAW_SENTINEL2 / f"sentinel2_{y}.tif").exists() and not (
                    config.DATA_RAW_LANDSAT / f"landsat_{y}.tif"
                ).exists():
                    errors.append(f"glacier_areas_all_years.csv row year={y} has no raw source")

    if errors:
        print("DATA COVERAGE VALIDATION FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Data coverage validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
