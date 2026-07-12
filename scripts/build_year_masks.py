#!/usr/bin/env python3
"""Build yearly RGI glacier masks aligned to Sentinel-2 rasters."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, preprocessing  # noqa: E402


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


def load_rgi():
    import geopandas as gpd

    rgi_path = config.DATA_RGI / "rgi_study_area.shp"
    if not rgi_path.exists():
        raise FileNotFoundError(f"Missing RGI study-area shapefile: {rgi_path}")
    rgi = gpd.read_file(rgi_path)
    if len(rgi) == 0:
        raise ValueError(f"RGI study-area shapefile is empty: {rgi_path}")
    return rgi


def mask_stats(mask_path: Path, source_path: Path) -> dict:
    with rasterio.open(source_path) as src, rasterio.open(mask_path) as mask_src:
        if (mask_src.height, mask_src.width) != (src.height, src.width):
            raise ValueError(f"{mask_path.name}: shape does not match {source_path.name}")
        if mask_src.crs != src.crs:
            raise ValueError(f"{mask_path.name}: CRS does not match {source_path.name}")
        if mask_src.transform != src.transform:
            raise ValueError(f"{mask_path.name}: transform does not match {source_path.name}")
        mask = mask_src.read(1)

    values = np.unique(mask)
    if not set(int(v) for v in values).issubset({0, 1}):
        raise ValueError(f"{mask_path.name}: expected binary values, got {values.tolist()}")
    glacier_pixels = int(mask.sum())
    total_pixels = int(mask.size)
    if glacier_pixels <= 0:
        raise ValueError(f"{mask_path.name}: contains no glacier pixels")
    return {
        "shape": [int(mask.shape[0]), int(mask.shape[1])],
        "glacier_pixels": glacier_pixels,
        "total_pixels": total_pixels,
        "glacier_fraction": float(glacier_pixels / total_pixels),
    }


def build_year(year: int, rgi, overwrite: bool) -> dict:
    source_path = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    if not source_path.exists():
        raise FileNotFoundError(f"Missing Sentinel-2 raster for {year}: {source_path}")

    mask_path = config.DATA_MASKS / f"mask_{year}.tif"
    created = False
    if overwrite or not mask_path.exists():
        preprocessing.rasterize_rgi_to_mask(rgi, source_path, mask_path)
        created = True

    stats = mask_stats(mask_path, source_path)
    return {
        "year": year,
        "source_file": str(source_path.relative_to(ROOT)),
        "mask_file": str(mask_path.relative_to(ROOT)),
        "source_flag": "sentinel2_sr",
        "created_this_run": created,
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2016-2024", help="Comma/range list, for example 2016-2024 or 2021,2024")
    parser.add_argument("--include-2015", action="store_true", help="Allow 2015 TOA fallback mask generation")
    parser.add_argument("--overwrite", action="store_true", help="Rebuild existing masks")
    parser.add_argument("--manifest", type=Path, default=config.DATA_MASKS / "manifest.json")
    args = parser.parse_args()

    years = parse_years(args.years)
    if 2015 in years and not args.include_2015:
        raise ValueError("2015 is a late-year TOA fallback. Pass --include-2015 to build it explicitly.")

    rgi = load_rgi()
    config.DATA_MASKS.mkdir(parents=True, exist_ok=True)
    entries = []
    for year in years:
        print(f"Building mask for {year}...")
        entries.append(build_year(year, rgi, args.overwrite))

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "years_requested": years,
        "excluded_years": [2015] if 2015 not in years else [],
        "rgi_file": str((config.DATA_RGI / "rgi_study_area.shp").relative_to(ROOT)),
        "mask_role": "training_label_rasterization",
        "notes": [
            "Masks are rasterized from RGI study-area polygons onto each Sentinel-2 raster grid.",
            "2015 is excluded by default because it is a late-year TOA fallback, not strict summer SR.",
        ],
        "years": entries,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest -> {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
