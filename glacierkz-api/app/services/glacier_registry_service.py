"""Verified RGI glacier registry and per-glacier mask statistics."""

from __future__ import annotations

import csv
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException


def _resolve_core_dir() -> Path:
    configured = os.environ.get("CORE_DIR")
    here = Path(__file__).resolve()
    candidates = [
        Path(configured) if configured else None,
        here.parents[3],
        here.parents[2],
        here.parents[2].parent,
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "data" / "rgi" / "rgi_study_area.shp").is_file():
            return candidate
    return Path(configured) if configured else here.parents[3]


CORE_DIR = _resolve_core_dir()
RGI_PATH = CORE_DIR / "data" / "rgi" / "rgi_study_area.shp"
PREDICTIONS_DIR = CORE_DIR / "predictions"
WGMS_TUYUKSU = CORE_DIR / "data" / "wgms" / "tuyuksu_areas.csv"

KNOWN_NAMES = {
    "RGI2000-v7.0-G-13-33843": {
        "name": "Tsentralniy Tuyuksu Glacier",
        "name_ru": "Ледник Центральный Туюксу",
        "priority": 1,
        "wgms_reference": True,
    },
    "RGI2000-v7.0-G-13-33845": {
        "name": "Bogdanovich Glacier",
        "name_ru": "Ледник Богдановича",
        "priority": 2,
        "wgms_reference": False,
    },
}


@lru_cache(maxsize=1)
def _load_rgi():
    if not RGI_PATH.is_file():
        raise FileNotFoundError(f"RGI study-area file is missing: {RGI_PATH}")
    import geopandas as gpd

    frame = gpd.read_file(RGI_PATH)
    if frame.crs is None:
        raise ValueError("RGI study-area file has no CRS")
    return frame.to_crs("EPSG:4326")


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def _record(row, include_geometry: bool = False) -> dict[str, Any]:
    rgi_id = str(row["rgi_id"])
    known = KNOWN_NAMES.get(rgi_id, {})
    source_name = _clean(row.get("glac_name"))
    name = known.get("name") or source_name or f"Unnamed glacier {rgi_id.rsplit('-', 1)[-1]}"
    result = {
        "rgi_id": rgi_id,
        "name": name,
        "name_ru": known.get("name_ru") or source_name or name,
        "named": bool(known or source_name),
        "priority": known.get("priority"),
        "wgms_reference": bool(known.get("wgms_reference")),
        "glims_id": _clean(row.get("glims_id")),
        "subregion": _clean(row.get("o2region")),
        "centroid": {
            "longitude": float(row["cenlon"]),
            "latitude": float(row["cenlat"]),
        },
        "rgi_area_km2": round(float(row["area_km2"]), 6),
        "elevation": {
            "min_m": round(float(row["zmin_m"]), 1),
            "mean_m": round(float(row["zmean_m"]), 1),
            "max_m": round(float(row["zmax_m"]), 1),
        },
        "slope_deg": round(float(row["slope_deg"]), 2),
        "aspect_deg": round(float(row["aspect_deg"]), 2),
        "maximum_length_m": int(row["lmax_m"]),
        "dem_source": _clean(row.get("dem_source")),
        "inventory_date": _clean(row.get("src_date")),
    }
    if include_geometry:
        from shapely.geometry import mapping

        result["geometry"] = mapping(row.geometry)
    return result


def list_glaciers(
    search: str = "",
    named_only: bool = False,
    min_area_km2: float = 0.0,
    offset: int = 0,
    limit: int = 50,
    include_geometry: bool = False,
) -> dict[str, Any]:
    frame = _load_rgi()
    records = [_record(row, include_geometry=include_geometry) for _, row in frame.iterrows()]
    if search:
        query = search.casefold()
        records = [
            record
            for record in records
            if query in record["rgi_id"].casefold()
            or query in record["name"].casefold()
            or query in record["name_ru"].casefold()
        ]
    if named_only:
        records = [record for record in records if record["named"]]
    records = [record for record in records if record["rgi_area_km2"] >= min_area_km2]
    records.sort(
        key=lambda record: (
            record["priority"] is None,
            record["priority"] or 999,
            -record["rgi_area_km2"],
        )
    )
    return {
        "glaciers": records[offset : offset + limit],
        "total": len(records),
        "offset": offset,
        "limit": limit,
        "source": "Randolph Glacier Inventory 7.0, study-area subset",
    }


def get_glacier(rgi_id: str, include_geometry: bool = True) -> dict[str, Any]:
    frame = _load_rgi()
    selected = frame[frame["rgi_id"] == rgi_id]
    if selected.empty:
        raise HTTPException(404, f"Glacier {rgi_id!r} is not present in the local RGI subset")
    return _record(selected.iloc[0], include_geometry=include_geometry)


def _available_years(method: str) -> list[int]:
    if not PREDICTIONS_DIR.is_dir():
        return []
    return sorted(
        int(directory.name)
        for directory in PREDICTIONS_DIR.iterdir()
        if directory.is_dir() and directory.name.isdigit() and (directory / f"{method}_mask.tif").is_file()
    )


def _wgms_series(rgi_id: str) -> list[dict[str, Any]]:
    if rgi_id != "RGI2000-v7.0-G-13-33843" or not WGMS_TUYUKSU.is_file():
        return []
    with WGMS_TUYUKSU.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        {
            "year": int(row["year"]),
            "area_km2": float(row["area_km2"]),
            "source": row.get("source", "WGMS"),
        }
        for row in rows
    ]


@lru_cache(maxsize=4096)
def glacier_timeseries(rgi_id: str, method: str = "ndsi") -> dict[str, Any]:
    method = method.lower()
    if method not in {"ndsi", "rf", "unet"}:
        raise HTTPException(400, "Method must be one of: ndsi, rf, unet")
    glacier = get_glacier(rgi_id, include_geometry=True)
    geometry = glacier["geometry"]
    points: list[dict[str, Any]] = []

    import numpy as np
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import transform_geom

    for year in _available_years(method):
        path = PREDICTIONS_DIR / str(year) / f"{method}_mask.tif"
        with rasterio.open(path) as src:
            transformed = transform_geom("EPSG:4326", src.crs, geometry)
            data, _ = mask(src, [transformed], crop=True, filled=True, indexes=1)
            glacier_pixels = int(np.count_nonzero(data > 0))
            pixel_area_km2 = abs(src.transform.a * src.transform.e - src.transform.b * src.transform.d) / 1_000_000
            area_km2 = glacier_pixels * pixel_area_km2
        points.append(
            {
                "year": year,
                "area_km2": round(area_km2, 4),
                "coverage_of_rgi_percent": round(area_km2 / glacier["rgi_area_km2"] * 100, 2)
                if glacier["rgi_area_km2"]
                else None,
                "method": method,
                "mask_url": f"/static/predictions/{year}/{method}_mask.tif",
            }
        )

    change = None
    change_percent = None
    if len(points) >= 2:
        change = round(points[-1]["area_km2"] - points[0]["area_km2"], 4)
        if points[0]["area_km2"]:
            change_percent = round(change / points[0]["area_km2"] * 100, 2)
    return {
        # Return the exact inventory boundary used for the raster clip so clients
        # can render and audit the spatial scope of every observation.
        "glacier": glacier,
        "method": method,
        "points": points,
        "first_year": points[0]["year"] if points else None,
        "last_year": points[-1]["year"] if points else None,
        "change_km2": change,
        "change_percent": change_percent,
        "wgms_points": _wgms_series(rgi_id),
        "scope": "prediction pixels measured inside the fixed RGI 2000 inventory polygon",
        "caveat": (
            "This series is clipped to a fixed RGI 2000 outline. It is useful for consistent "
            "screening and expert review, but is not an independently delineated annual glacier boundary."
        ),
    }


def glacier_report(rgi_id: str, method: str = "ndsi") -> dict[str, Any]:
    series = glacier_timeseries(rgi_id, method)
    glacier = series["glacier"]
    return {
        "schema": "glaciernet-kz.glacier-report.v1",
        "title": f"GlacierNET-KZ evidence card: {glacier['name']}",
        "glacier": glacier,
        "timeseries": series,
        "claims_allowed": [
            "RGI inventory description",
            "within-outline model screening",
            "comparison requiring expert interpretation",
        ],
        "claims_not_allowed": [
            "field-validated annual boundary",
            "ice volume or water-supply forecast",
            "operational hazard decision without expert review",
        ],
        "sources": [
            source
            for source in [
                "Randolph Glacier Inventory 7.0",
                "Local GlacierNET-KZ prediction masks",
                "WGMS Fluctuations of Glaciers" if glacier["wgms_reference"] else None,
            ]
            if source
        ],
    }
