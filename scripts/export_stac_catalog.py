#!/usr/bin/env python3
"""
Export a STAC 1.0.0 Collection catalog for GlacierNET-KZ study area.

Enables discovery in QGIS STAC plugin, STAC Browser, and planetary-scale
geospatial workflows (FAIR interoperability).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    GLACIERS,
    PROJECT_ROOT,
    STUDY_AREA_BBOX,
    SUMMER_END_MONTH_DAY,
    SUMMER_START_MONTH_DAY,
    YEARS_LANDSAT,
    YEARS_SENTINEL2,
)

REPO_URL = "https://github.com/nicklaua/GlacierNET-KZ"
LICENSE = "MIT"


def _bbox_west_south_east_north() -> list[float]:
    min_lon, min_lat, max_lon, max_lat = STUDY_AREA_BBOX
    return [min_lon, min_lat, max_lon, max_lat]


def build_collection() -> dict:
    """Build STAC Collection JSON for the Ili Alatau study area."""
    min_lon, min_lat, max_lon, max_lat = STUDY_AREA_BBOX
    all_years = sorted(set(YEARS_LANDSAT + YEARS_SENTINEL2))
    temporal_start = f"{min(all_years)}-{SUMMER_START_MONTH_DAY}T00:00:00Z"
    temporal_end = f"{max(all_years)}-{SUMMER_END_MONTH_DAY}T23:59:59Z"

    glacier_summaries = [
        {
            "id": gid,
            "name_en": g.get("name_en", g.get("name_ru")),
            "name_ru": g.get("name_ru"),
            "coordinates": [g["lon"], g["lat"]],
            "rgi_id": g.get("rgi_id"),
            "priority": g.get("priority"),
        }
        for gid, g in GLACIERS.items()
    ]

    return {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": "glaciernet-kz-ili-alatau",
        "title": "GlacierNET-KZ — Ili Alatau Glacier Monitoring",
        "description": (
            "Deep-learning glacier segmentation and multi-decadal area time series "
            "for the Zailiysky (Ili) Alatau, Kazakhstan. Sentinel-2 and Landsat "
            "summer composites, U-Net masks, WGMS Tuyuksu validation."
        ),
        "keywords": [
            "glacier",
            "kazakhstan",
            "ili-alatau",
            "tian-shan",
            "sentinel-2",
            "landsat",
            "u-net",
            "segmentation",
            "climate-change",
        ],
        "license": LICENSE,
        "providers": [
            {
                "name": "GlacierNET-KZ",
                "roles": ["producer", "licensor"],
                "url": REPO_URL,
            },
            {
                "name": "Copernicus / ESA",
                "roles": ["originator"],
                "url": "https://www.copernicus.eu/",
            },
            {
                "name": "USGS",
                "roles": ["originator"],
                "url": "https://www.usgs.gov/",
            },
        ],
        "extent": {
            "spatial": {"bbox": [[min_lon, min_lat, max_lon, max_lat]]},
            "temporal": {"interval": [[temporal_start, temporal_end]]},
        },
        "summaries": {
            "platform": ["sentinel-2a", "sentinel-2b", "landsat-5", "landsat-7", "landsat-8"],
            "gsd": [10, 30],
            "processing:level": ["L2A", "L2SP"],
            "glaciers": glacier_summaries,
            "model_metrics": {"unet_f1": 0.876, "unet_iou": 0.780},
        },
        "links": [
            {"rel": "root", "href": "./catalog.json", "type": "application/json"},
            {"rel": "self", "href": "./catalog.json", "type": "application/json"},
            {"rel": "license", "href": f"{REPO_URL}/blob/main/LICENSE", "type": "text/plain"},
            {"rel": "describedby", "href": f"{REPO_URL}/blob/main/docs/DATA_CITATION.md", "type": "text/html"},
            {"rel": "cite-as", "href": f"{REPO_URL}/blob/main/CITATION.cff", "type": "application/yaml"},
        ],
        "stac_extensions": [
            "https://stac-extensions.github.io/processing/v1.1.0/schema.json",
        ],
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def export_catalog(output: Path) -> Path:
    """Write STAC Collection JSON to disk."""
    output.parent.mkdir(parents=True, exist_ok=True)
    catalog = build_collection()
    output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Export GlacierNET-KZ STAC Collection catalog")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "stac" / "catalog.json",
        help="Output path for catalog.json",
    )
    args = parser.parse_args()
    path = export_catalog(args.output)
    print(f"STAC catalog written to {path}")


if __name__ == "__main__":
    main()
