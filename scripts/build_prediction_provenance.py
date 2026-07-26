#!/usr/bin/env python3
"""Backfill reproducible provenance manifests for existing local predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import list_available_years  # noqa: E402
from src import config  # noqa: E402
from src.provenance import build_prediction_provenance, merge_prediction_provenance  # noqa: E402


def source_path(year: int) -> Path:
    sentinel2 = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    if sentinel2.is_file():
        return sentinel2
    landsat = config.DATA_RAW_LANDSAT / f"landsat_{year}.tif"
    if landsat.is_file():
        return landsat
    raise FileNotFoundError(f"No source raster for {year}")


def main() -> int:
    completed = 0
    for item in list_available_years():
        year = int(item["year"])
        prediction_dir = ROOT / "predictions" / str(year)
        results_path = prediction_dir / "results.json"
        if not results_path.is_file():
            continue
        results = json.loads(results_path.read_text(encoding="utf-8"))
        model_names = [
            name
            for name in ("ndsi", "rf", "unet")
            if name in results and (prediction_dir / f"{name}_mask.tif").is_file()
        ]
        if not model_names:
            continue
        record = build_prediction_provenance(
            root=ROOT,
            year=year,
            source_path=source_path(year),
            prediction_dir=prediction_dir,
            model_names=model_names,
            ndsi_threshold=config.BEST_NDSI_THRESHOLD,
            use_tta=False,
        )
        merge_prediction_provenance(prediction_dir / "provenance.json", record)
        completed += 1
        print(f"[{completed}] {year}: {', '.join(model_names)}", flush=True)
    print(f"Wrote provenance manifests for {completed} prediction years.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
