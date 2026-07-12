#!/usr/bin/env python3
"""Validate yearly Sentinel-2 training masks against source rasters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


def parse_years(raw: str) -> list[int]:
    years: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            years.extend(range(start, end + 1))
        else:
            years.append(int(part))
    return sorted(dict.fromkeys(years))


def validate_year(year: int) -> list[str]:
    errors: list[str] = []
    source_path = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    mask_path = config.DATA_MASKS / f"mask_{year}.tif"
    if not source_path.exists():
        return [f"{year}: missing source raster {source_path.relative_to(ROOT)}"]
    if not mask_path.exists():
        return [f"{year}: missing mask {mask_path.relative_to(ROOT)}"]

    with rasterio.open(source_path) as src, rasterio.open(mask_path) as mask_src:
        if mask_src.count != 1:
            errors.append(f"{year}: mask must have one band, got {mask_src.count}")
        if str(mask_src.dtypes[0]) != "uint8":
            errors.append(f"{year}: mask dtype must be uint8, got {mask_src.dtypes[0]}")
        if (mask_src.height, mask_src.width) != (src.height, src.width):
            errors.append(f"{year}: mask shape {(mask_src.height, mask_src.width)} != source {(src.height, src.width)}")
        if mask_src.crs != src.crs:
            errors.append(f"{year}: mask CRS {mask_src.crs} != source {src.crs}")
        if mask_src.transform != src.transform:
            errors.append(f"{year}: mask transform does not match source transform")
        mask = mask_src.read(1)

    values = np.unique(mask)
    if not set(int(v) for v in values).issubset({0, 1}):
        errors.append(f"{year}: mask values must be binary 0/1, got {values.tolist()}")
    if int(mask.sum()) <= 0:
        errors.append(f"{year}: mask contains no glacier pixels")
    return errors


def validate_manifest(manifest_path: Path, require_years: list[int]) -> list[str]:
    if not manifest_path.exists():
        return [f"missing mask manifest {manifest_path.relative_to(ROOT)}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("years")
    if not isinstance(entries, list):
        return [f"{manifest_path.relative_to(ROOT)}: years must be a list"]
    manifest_years = sorted(int(entry.get("year")) for entry in entries)
    if manifest_years != require_years:
        return [f"manifest years {manifest_years} != required years {require_years}"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2016-2024", help="Comma/range list, for example 2016-2024 or 2021")
    parser.add_argument("--allow-2015", action="store_true", help="Allow 2015 TOA fallback in validation")
    parser.add_argument("--manifest", type=Path, default=config.DATA_MASKS / "manifest.json")
    parser.add_argument("--skip-manifest", action="store_true")
    args = parser.parse_args()

    years = parse_years(args.years)
    errors: list[str] = []
    if 2015 in years and not args.allow_2015:
        errors.append("2015 fallback must not be included in strict Sentinel-2 training mask validation")
    for year in years:
        errors.extend(validate_year(year))
    if not args.skip_manifest:
        errors.extend(validate_manifest(args.manifest, years))

    if errors:
        print("TRAINING MASK VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Training mask validation passed for years: {years}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
