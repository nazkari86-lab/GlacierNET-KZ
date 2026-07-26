#!/usr/bin/env python3
"""Report pipeline coverage: which years have data, patches, predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from src import config

    report = config.RESULTS_DIR / "pipeline_status.json"
    status = {
        "sentinel2_years_target": config.YEARS_SENTINEL2,
        "landsat_years_target": config.YEARS_LANDSAT,
        "raw_sentinel2": [],
        "raw_landsat": [],
        "training_masks": [],
        "mask_manifest": None,
        "patches": [],
        "patch_manifests": [],
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

    if config.DATA_MASKS.exists():
        status["training_masks"] = sorted(
            int(path.stem.split("_")[-1])
            for path in config.DATA_MASKS.glob("mask_*.tif")
            if path.stem.split("_")[-1].isdigit()
        )
        manifest_path = config.DATA_MASKS / "manifest.json"
        if manifest_path.exists():
            status["mask_manifest"] = str(manifest_path.relative_to(ROOT))

    if config.DATA_PATCHES.exists():
        manifest_paths = sorted(config.DATA_PATCHES.glob("**/manifest.json"))
        status["patch_manifests"] = [str(path.relative_to(ROOT)) for path in manifest_paths]
        patch_years: set[int] = set()
        for manifest_path in manifest_paths:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                patch_years.update(
                    int(entry["year"])
                    for entry in manifest.get("years", [])
                    if isinstance(entry, dict) and str(entry.get("year", "")).isdigit()
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        status["patches"] = sorted(patch_years)

    pred_dir = ROOT / "predictions"
    if pred_dir.exists():
        status["predictions"] = sorted(int(p.name) for p in pred_dir.iterdir() if p.is_dir() and p.name.isdigit())

    report.write_text(json.dumps(status, indent=2), encoding="utf-8")

    print("Pipeline Status")
    print("=" * 50)
    print(f"Sentinel-2 raw:  {status['raw_sentinel2'] or 'NONE (download via notebook 01)'}")
    print(f"  Missing:       {status['missing_sentinel2']}")
    print(f"Landsat raw:     {status['raw_landsat'] or 'NONE'}")
    print(f"  Missing:       {status['missing_landsat']}")
    print(f"Training masks:  {status['training_masks']}")
    print(f"Patches:         {status['patches']}")
    print(f"Patch manifests: {len(status['patch_manifests'])}")
    print(f"Predictions:     {status['predictions']}")
    print(f"\nReport → {report}")

    if status["missing_sentinel2"]:
        print("\nNext step: Run notebooks/01_data_download.ipynb for missing Sentinel-2 years")
        print("  Requires: earthengine authenticate (local machine)")


if __name__ == "__main__":
    main()
