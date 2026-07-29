#!/usr/bin/env python3
"""Build compact, reproducible HydroRIVERS and HydroBASINS map layers for Risk Twin.

The original HydroSHEDS Asia files are deliberately kept untouched.  This
script reads only the local RGI study-area extent plus a modest context margin,
then writes small GeoPackages the API can load on every request.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
WGS84 = "EPSG:4326"
RGI = ROOT / "data/rgi/rgi_study_area.shp"
RIVERS_SOURCE = ROOT / "data/hydrology/hydrorivers_as/HydroRIVERS_v10_as.gdb"
BASINS_SOURCE = ROOT / "data/hydrology/hydrobasins_as/hybas_as_lev06_v1c.shp"
OUTPUT_DIR = ROOT / "data/hydrology/subsets"
RIVERS_OUTPUT = OUTPUT_DIR / "hydrorivers_study_area.gpkg"
BASINS_OUTPUT = OUTPUT_DIR / "hydrobasins_level06_study_area.gpkg"
MANIFEST = OUTPUT_DIR / "manifest.json"
CONTEXT_MARGIN_DEGREES = 0.30


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_record(path: Path, feature_count: int) -> dict[str, object]:
    return {
        "path": str(path.relative_to(ROOT)),
        "feature_count": feature_count,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> None:
    missing = [path for path in (RGI, RIVERS_SOURCE, BASINS_SOURCE) if not path.exists()]
    if missing:
        raise SystemExit(
            "Missing required local input(s): " + ", ".join(str(path.relative_to(ROOT)) for path in missing)
        )

    study_area = gpd.read_file(RGI).to_crs(WGS84)
    west, south, east, north = study_area.total_bounds
    bbox = (
        west - CONTEXT_MARGIN_DEGREES,
        south - CONTEXT_MARGIN_DEGREES,
        east + CONTEXT_MARGIN_DEGREES,
        north + CONTEXT_MARGIN_DEGREES,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rivers = gpd.read_file(RIVERS_SOURCE, bbox=bbox).to_crs(WGS84)
    basins = gpd.read_file(BASINS_SOURCE, bbox=bbox).to_crs(WGS84)
    rivers.to_file(RIVERS_OUTPUT, layer="hydrorivers", driver="GPKG")
    basins.to_file(BASINS_OUTPUT, layer="hydrobasins_level06", driver="GPKG")

    manifest = {
        "schema": "glaciernet-kz.risk-twin-hydrology-subsets.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "HydroSHEDS HydroRIVERS v1.0 and HydroBASINS v1c, Asia local files",
        "study_area_bbox_wgs84": [round(value, 6) for value in study_area.total_bounds],
        "subset_bbox_wgs84": [round(value, 6) for value in bbox],
        "context_margin_degrees": CONTEXT_MARGIN_DEGREES,
        "outputs": [output_record(RIVERS_OUTPUT, len(rivers)), output_record(BASINS_OUTPUT, len(basins))],
        "scope": "Map and proximity context only. This subset does not calculate flow paths, inundation, downstream exposure, or event probability.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
