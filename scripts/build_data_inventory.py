#!/usr/bin/env python3
"""Build a reproducible inventory for local geospatial inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

OUT_CSV = config.TABLES_DIR / "data_inventory.csv"
OUT_JSON = config.RESULTS_DIR / "data_inventory.json"


def sha256_prefix(path: Path, chunk_size: int = 1024 * 1024, max_bytes: int = 64 * 1024 * 1024) -> str:
    """Hash the first max_bytes so inventory is fast but still change-sensitive."""
    h = hashlib.sha256()
    read = 0
    with path.open("rb") as f:
        while read < max_bytes:
            chunk = f.read(min(chunk_size, max_bytes - read))
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
    return h.hexdigest()


def year_from_name(path: Path) -> int | None:
    match = re.search(r"(19|20)\d{2}", path.name)
    return int(match.group(0)) if match else None


def raster_row(path: Path, sensor: str) -> dict:
    import rasterio

    with rasterio.open(path) as src:
        bounds = src.bounds
        row = {
            "path": str(path.relative_to(ROOT)),
            "sensor": sensor,
            "year": year_from_name(path),
            "bands": src.count,
            "dtype": ",".join(sorted(set(src.dtypes))),
            "crs": str(src.crs),
            "height": src.height,
            "width": src.width,
            "pixel_size_x": abs(src.res[0]),
            "pixel_size_y": abs(src.res[1]),
            "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
            "sha256_first64mb": sha256_prefix(path),
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "notes": "",
        }
    if path.name == "sentinel2_2015.tif":
        row["notes"] = "Fallback Sentinel-2 TOA annual late-2015 composite; no summer L2A/SR scenes for AOI."
    elif sensor == "sentinel2" and row["bands"] == 7:
        row["notes"] = "Compact reflectance-only export; indices are derived locally by src.data_loader.load_image()."
    return row


def main() -> None:
    rows = []
    for path in sorted(config.DATA_RAW_SENTINEL2.glob("sentinel2_*.tif")):
        rows.append(raster_row(path, "sentinel2"))
    for path in sorted(config.DATA_RAW_LANDSAT.glob("landsat_*.tif")):
        rows.append(raster_row(path, "landsat"))

    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "sensor",
        "year",
        "bands",
        "dtype",
        "crs",
        "height",
        "width",
        "pixel_size_x",
        "pixel_size_y",
        "size_mb",
        "sha256_first64mb",
        "bounds",
        "notes",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    OUT_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(rows)} rows -> {OUT_CSV}")
    print(f"Wrote {len(rows)} rows -> {OUT_JSON}")


if __name__ == "__main__":
    main()
