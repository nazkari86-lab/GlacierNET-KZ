#!/usr/bin/env python3
"""Report pipeline coverage: which years have data, patches, predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config

REPORT = config.RESULTS_DIR / "pipeline_status.json"


def main() -> None:
    status = {
        "sentinel2_years_target": config.YEARS_SENTINEL2,
        "landsat_years_target": config.YEARS_LANDSAT,
        "raw_sentinel2": [],
        "raw_landsat": [],
        "patches": [],
        "predictions": [],
        "missing_sentinel2": [],
        "missing_landsat": [],
    }

    for year in config.YEARS_SENTINEL2:
        raw = list(config.DATA_RAW_SENTINEL2.glob(f"*{year}*"))
        if raw:
            status["raw_sentinel2"].append(year)
        else:
            status["missing_sentinel2"].append(year)

    for year in config.YEARS_LANDSAT:
        raw = list(config.DATA_RAW_LANDSAT.glob(f"*{year}*"))
        if raw:
            status["raw_landsat"].append(year)
        else:
            status["missing_landsat"].append(year)

    if config.DATA_PATCHES.exists():
        status["patches"] = sorted(int(p.name) for p in config.DATA_PATCHES.iterdir() if p.is_dir() and p.name.isdigit())

    pred_dir = ROOT / "predictions"
    if pred_dir.exists():
        status["predictions"] = sorted(int(p.name) for p in pred_dir.iterdir() if p.is_dir() and p.name.isdigit())

    REPORT.write_text(json.dumps(status, indent=2), encoding="utf-8")

    print("Pipeline Status")
    print("=" * 50)
    print(f"Sentinel-2 raw:  {status['raw_sentinel2'] or 'NONE (download via notebook 01)'}")
    print(f"  Missing:       {status['missing_sentinel2']}")
    print(f"Landsat raw:     {status['raw_landsat'] or 'NONE'}")
    print(f"  Missing:       {status['missing_landsat']}")
    print(f"Patches:         {status['patches']}")
    print(f"Predictions:     {status['predictions']}")
    print(f"\nReport → {REPORT}")

    if status["missing_sentinel2"]:
        print("\nNext step: Run notebooks/01_data_download.ipynb for missing Sentinel-2 years")
        print("  Requires: earthengine authenticate (local machine)")


if __name__ == "__main__":
    main()
