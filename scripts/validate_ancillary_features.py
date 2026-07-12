#!/usr/bin/env python3
"""Validate ancillary feature rasters against a Sentinel-2 reference grid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


def validate_alignment(reference_path: Path, terrain_path: Path, worldcover_path: Path) -> list[str]:
    import rasterio

    errors: list[str] = []
    with rasterio.open(reference_path) as reference:
        expected = (reference.height, reference.width, reference.crs, reference.transform)
    expected_height, expected_width, expected_crs, expected_transform = expected
    for path, count, dtype in ((terrain_path, 3, "float32"), (worldcover_path, 1, "uint8")):
        if not path.exists():
            errors.append(f"Missing ancillary raster: {path}")
            continue
        with rasterio.open(path) as dataset:
            if (dataset.height, dataset.width, dataset.crs, dataset.transform) != expected:
                errors.append(f"Grid mismatch: {path}")
            if dataset.count != count:
                errors.append(f"{path}: expected {count} bands, found {dataset.count}")
            if any(item != dtype for item in dataset.dtypes):
                errors.append(f"{path}: expected {dtype}, found {dataset.dtypes}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=config.DATA_RAW_SENTINEL2 / "sentinel2_2020.tif")
    parser.add_argument("--terrain", type=Path, default=ROOT / "data/ancillary/terrain/terrain_features.tif")
    parser.add_argument(
        "--worldcover", type=Path, default=ROOT / "data/ancillary/worldcover/worldcover_2021_aligned.tif"
    )
    args = parser.parse_args()
    errors = validate_alignment(args.reference, args.terrain, args.worldcover)
    if errors:
        print("ANCILLARY VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Ancillary feature validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
