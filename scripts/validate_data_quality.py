#!/usr/bin/env python3
"""Validate local data completeness and schema consistency."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, data_loader  # noqa: E402

OUT = config.RESULTS_DIR / "data_quality_report.json"


def open_raster_with_retry(path: Path, attempts: int = 3):
    import rasterio
    from rasterio.errors import RasterioIOError

    last_error: RasterioIOError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return rasterio.open(path)
        except RasterioIOError as error:
            last_error = error
            if "Interrupted system call" not in str(error) or attempt == attempts:
                raise
            time.sleep(0.25 * attempt)
    raise last_error or RuntimeError(f"Could not open raster: {path}")


def expected_loaded_channels(path: Path) -> int:
    if path.name.startswith("sentinel2_"):
        return config.N_CHANNELS
    if path.name.startswith("landsat_"):
        return 9
    raise ValueError(f"Unknown raster sensor for {path}")


def validate_raster(path: Path, expected_shape: tuple[int, int] | None) -> tuple[dict, list[str]]:
    errors: list[str] = []
    with open_raster_with_retry(path) as src:
        shape = (src.height, src.width)
        if str(src.crs) != config.EXPORT_CRS:
            errors.append(f"{path.name}: CRS {src.crs} != {config.EXPORT_CRS}")
        if expected_shape is not None and shape != expected_shape:
            errors.append(f"{path.name}: shape {shape} != {expected_shape}")
        if src.count not in (7, 9, 11):
            errors.append(f"{path.name}: unexpected band count {src.count}")
        expected_channels = expected_loaded_channels(path)
        loaded_channels = data_loader.load_image(path).shape[-1]
        if loaded_channels != expected_channels:
            errors.append(f"{path.name}: load_image channels {loaded_channels} != {expected_channels}")
        row = {
            "path": str(path.relative_to(ROOT)),
            "bands": src.count,
            "dtype": sorted(set(src.dtypes)),
            "shape": shape,
            "crs": str(src.crs),
            "loaded_channels": loaded_channels,
            "expected_loaded_channels": expected_channels,
            "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
        }
    return row, errors


def main() -> int:
    rows: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []

    sentinel_paths = {int(p.stem.split("_")[1]): p for p in config.DATA_RAW_SENTINEL2.glob("sentinel2_*.tif")}
    landsat_paths = {int(p.stem.split("_")[1]): p for p in config.DATA_RAW_LANDSAT.glob("landsat_*.tif")}

    missing_s2 = sorted(set(config.YEARS_SENTINEL2) - set(sentinel_paths))
    missing_landsat = sorted(set(config.YEARS_LANDSAT) - set(landsat_paths))
    if missing_s2:
        errors.append(f"Missing Sentinel-2 years: {missing_s2}")
    if missing_landsat:
        errors.append(f"Missing Landsat years: {missing_landsat}")

    expected_shape = None
    for path in sorted(sentinel_paths.values()) + sorted(landsat_paths.values()):
        if expected_shape is None:
            with open_raster_with_retry(path) as src:
                expected_shape = (src.height, src.width)
        row, row_errors = validate_raster(path, expected_shape)
        rows.append(row)
        errors.extend(row_errors)

    if 2015 in sentinel_paths:
        warnings.append(
            "sentinel2_2015.tif is an annual late-2015 TOA fallback; no summer L2A/SR scenes exist for AOI."
        )
    compact = [r["path"] for r in rows if r["path"].startswith("data/raw/sentinel2") and r["bands"] == 7]
    if compact:
        warnings.append(f"Compact Sentinel-2 rasters detected and supported by load_image(): {compact}")
    if landsat_paths:
        warnings.append(
            "Landsat rasters load as 9-channel historical inputs; 11-channel U-Net training uses Sentinel-2 patches."
        )

    report = {
        "ok": not errors,
        "sentinel2_years": sorted(sentinel_paths),
        "landsat_years": sorted(landsat_paths),
        "expected_shape": expected_shape,
        "rasters": rows,
        "warnings": warnings,
        "errors": errors,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Data quality ok={report['ok']} -> {OUT}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
