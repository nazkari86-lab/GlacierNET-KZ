#!/usr/bin/env python3
"""Rebuild results/tables/glacier_areas_all_years.csv from predictions/ + raw metadata."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import rasterio  # noqa: E402

from predict import list_available_years  # noqa: E402
from src import config  # noqa: E402

OUT = config.TABLES_DIR / "glacier_areas_all_years.csv"
METHOD_MAP = {"ndsi": "NDSI", "rf": "RF", "unet": "U-Net"}


def sensor_for_year(year: int) -> str:
    if (config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif").exists():
        return "Sentinel-2"
    if (config.DATA_RAW_LANDSAT / f"landsat_{year}.tif").exists():
        return "Landsat"
    return "unknown"


def source_file_for_year(year: int) -> str:
    s2 = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    ls = config.DATA_RAW_LANDSAT / f"landsat_{year}.tif"
    if s2.exists():
        return str(s2.relative_to(config.PROJECT_ROOT))
    if ls.exists():
        return str(ls.relative_to(config.PROJECT_ROOT))
    return ""


def read_mask_stats(mask_path: Path) -> tuple[int, int, float]:
    with rasterio.open(mask_path) as src:
        mask = src.read(1)
        pixel_area = abs(src.res[0] * src.res[1])
    glacier_pixels = int(mask.sum())
    total_pixels = int(mask.size)
    area_km2 = glacier_pixels * pixel_area / 1e6
    return glacier_pixels, total_pixels, round(area_km2, 2)


def main() -> None:
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pred_dir = ROOT / "predictions"

    rows: list[dict[str, str | int | float]] = []
    for item in list_available_years():
        year = item["year"]
        year_dir = pred_dir / str(year)
        results_json = year_dir / "results.json"

        if results_json.exists():
            data = json.loads(results_json.read_text(encoding="utf-8"))
            for method_key, stats in data.items():
                method = METHOD_MAP.get(method_key, method_key.upper())
                rows.append(
                    {
                        "year": year,
                        "sensor": sensor_for_year(year),
                        "method": method,
                        "area_km2": stats["area_km2"],
                        "glacier_pixels": stats["glacier_pixels"],
                        "total_pixels": stats["total_pixels"],
                        "source_file": source_file_for_year(year),
                        "created_at": created_at,
                    }
                )
            continue

        for method_key, method_label in METHOD_MAP.items():
            mask_path = year_dir / f"{method_key}_mask.tif"
            if not mask_path.exists():
                continue
            gp, tp, area = read_mask_stats(mask_path)
            rows.append(
                {
                    "year": year,
                    "sensor": sensor_for_year(year),
                    "method": method_label,
                    "area_km2": area,
                    "glacier_pixels": gp,
                    "total_pixels": tp,
                    "source_file": source_file_for_year(year),
                    "created_at": created_at,
                }
            )

    rows.sort(key=lambda r: (int(r["year"]), str(r["method"])))

    fieldnames = [
        "year",
        "sensor",
        "method",
        "area_km2",
        "glacier_pixels",
        "total_pixels",
        "source_file",
        "created_at",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    years_covered = sorted({int(r["year"]) for r in rows})
    print(f"Wrote {len(rows)} rows for {len(years_covered)} years → {OUT}")
    print(f"Years: {years_covered}")


if __name__ == "__main__":
    main()
