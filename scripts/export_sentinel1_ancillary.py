#!/usr/bin/env python3
"""Submit reproducible Sentinel-1 summer-composite exports for multimodal ML."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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
            start, end = (int(value) for value in part.split("-", 1))
            years.extend(range(start, end + 1))
        else:
            years.append(int(part))
    return sorted(set(years))


def sentinel1_summer_composite(ee, year: int, aoi):
    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(f"{year}-07-01", f"{year}-10-01")
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
    )
    if collection.size().getInfo() == 0:
        return None
    # Store decibel values as int16 with scale factor 0.01 for compact Drive exports.
    return collection.median().multiply(100).toInt16().rename(["VV_x100", "VH_x100"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2016-2024")
    parser.add_argument("--folder", default="GlacierKZ")
    parser.add_argument("--project", default=None)
    parser.add_argument("--submit", action="store_true", help="Actually submit Google Drive export tasks")
    args = parser.parse_args()
    years = parse_years(args.years)
    if any(year < 2014 or year > 2100 for year in years):
        raise ValueError("Sentinel-1 export years must be in [2014, 2100]")

    import ee

    if args.project:
        ee.Initialize(project=args.project)
    else:
        ee.Initialize()
    aoi = ee.Geometry.Rectangle(list(config.STUDY_AREA_BBOX))
    manifest_entries = []
    for year in years:
        image = sentinel1_summer_composite(ee, year, aoi)
        entry = {
            "year": year,
            "expected_filename": f"sentinel1_{year}.tif",
            "bands": ["VV_x100", "VH_x100"],
            "scale_factor": 0.01,
            "offset": 0.0,
            "date_range": [f"{year}-07-01", f"{year}-10-01"],
            "state": "no_scenes" if image is None else "planned",
        }
        if image is not None and args.submit:
            task = ee.batch.Export.image.toDrive(
                image=image,
                description=f"sentinel1_{year}",
                folder=args.folder,
                fileNamePrefix=f"sentinel1_{year}",
                region=aoi,
                scale=config.EXPORT_SCALE_M,
                crs=config.EXPORT_CRS,
                maxPixels=1e11,
            )
            task.start()
            entry.update({"state": "submitted", "task_id": task.id})
        manifest_entries.append(entry)
        print(f"{year}: {entry['state']}")

    output_dir = ROOT / "data/ancillary/sentinel1"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "COPERNICUS/S1_GRD",
        "aoi_bbox_wgs84": list(config.STUDY_AREA_BBOX),
        "export_crs": config.EXPORT_CRS,
        "export_scale_m": config.EXPORT_SCALE_M,
        "entries": manifest_entries,
    }
    path = output_dir / "export_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
