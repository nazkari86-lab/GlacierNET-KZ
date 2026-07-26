#!/usr/bin/env python3
"""Sample annual Sentinel-2 GeoTIFFs and write acquisition QA indicators."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.acquisition_quality import acquisition_decision, assess_sentinel2_scene  # noqa: E402

FIELDS = [
    "year",
    "source_file",
    "sample_strategy",
    "cloud_fraction",
    "shadow_fraction",
    "snow_fraction",
    "off_glacier_snow_fraction",
    "nodata_fraction",
    "mean_ndsi",
    "valid_sample_pixels",
    "decision_status",
    "reason",
    "qa_method",
    "qa_caveat",
]


def sample_raster(path: Path, *, grid_size: int = 5, window_size: int = 128) -> np.ndarray:
    """Read small spatially distributed windows without decoding a full BigTIFF."""
    samples: list[np.ndarray] = []
    with rasterio.open(path) as dataset:
        if dataset.count < 6:
            raise ValueError(f"{path} has {dataset.count} bands; expected at least 6")
        row_centres = np.linspace(window_size // 2, dataset.height - window_size // 2, grid_size, dtype=int)
        col_centres = np.linspace(window_size // 2, dataset.width - window_size // 2, grid_size, dtype=int)
        for row in row_centres:
            for col in col_centres:
                window = Window(
                    max(0, col - window_size // 2),
                    max(0, row - window_size // 2),
                    min(window_size, dataset.width),
                    min(window_size, dataset.height),
                )
                sample = dataset.read(window=window, masked=True).filled(np.nan)
                valid = np.isfinite(sample).all(axis=0) & np.any(sample != 0, axis=0)
                # Cropped AOIs often occupy only part of the rectangular
                # GeoTIFF extent. Empty exterior tiles are not scene no-data.
                if valid.mean() < 0.01:
                    continue
                samples.append(sample.reshape(dataset.count, -1))
    if not samples:
        raise ValueError(f"{path} has no valid sampled windows")
    return np.concatenate(samples, axis=1)[:, np.newaxis, :]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/raw/sentinel2")
    parser.add_argument("--output", type=Path, default=ROOT / "results/tables/annual_scene_quality.csv")
    parser.add_argument("--grid-size", type=int, default=5)
    parser.add_argument("--window-size", type=int, default=128)
    args = parser.parse_args()

    rows = []
    for path in sorted(args.input_dir.glob("sentinel2_*.tif")):
        match = re.search(r"(20\d{2})", path.stem)
        if not match:
            continue
        quality = assess_sentinel2_scene(sample_raster(path, grid_size=args.grid_size, window_size=args.window_size))
        decision, reasons = acquisition_decision(quality)
        rows.append(
            {
                "year": int(match.group(1)),
                "source_file": str(path.relative_to(ROOT)),
                "sample_strategy": f"{args.grid_size}x{args.grid_size} windows of {args.window_size}px",
                **{key: quality[key] for key in FIELDS if key in quality},
                "decision_status": decision,
                "reason": "; ".join(reasons),
            }
        )
        print(f"{match.group(1)}: {decision}", flush=True)
    if not rows:
        raise FileNotFoundError(f"no annual Sentinel-2 GeoTIFFs found in {args.input_dir}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} scene QA rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
