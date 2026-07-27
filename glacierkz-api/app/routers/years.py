"""Read-only exploration of verified, on-disk yearly glacier results."""

from __future__ import annotations

import csv
import io
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/api/years", tags=["years"])


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
        if candidate is not None and (candidate / "results" / "tables").is_dir():
            return candidate
    return Path(configured) if configured else here.parents[3]


CORE_DIR = _resolve_core_dir()
TABLES_DIR = CORE_DIR / "results" / "tables"
PREDICTIONS_DIR = CORE_DIR / "predictions"


def _read_csv(name: str) -> list[dict[str, str]]:
    path = TABLES_DIR / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _artifact_url(year: int, filename: str) -> str | None:
    path = PREDICTIONS_DIR / str(year) / filename
    return f"/static/predictions/{year}/{filename}" if path.is_file() else None


def _map_mask(year: int) -> tuple[Path, str]:
    record = next((item for item in _build_year_records() if item["year"] == year), None)
    if record is None:
        raise HTTPException(404, f"No local result metadata for year {year}")
    preferred = str(record["primary_method"]).lower().replace("-", "")
    candidates = [preferred, *record["artifact_methods"], "ndsi", "rf", "unet"]
    for method in dict.fromkeys(candidates):
        path = PREDICTIONS_DIR / str(year) / f"{method}_mask.tif"
        if path.is_file():
            return path, method
    raise HTTPException(404, f"No physical map mask is available for year {year}")


def _map_layer_metadata(year: int) -> dict[str, Any]:
    path, method = _map_mask(year)
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(path) as source:
        west, south, east, north = transform_bounds(source.crs, "EPSG:4326", *source.bounds, densify_pts=21)
    return {
        "year": year,
        "method": method,
        "image_url": f"/api/years/{year}/map-layer.png",
        "bounds": [[south, west], [north, east]],
        "source": str(path.relative_to(CORE_DIR)),
        "scope": "georeferenced model segmentation screening layer",
        "caveat": "Not a field-validated annual glacier boundary or hazard layer.",
    }


@lru_cache(maxsize=48)
def _render_map_layer(path_string: str, modified_ns: int) -> bytes:
    del modified_ns  # The mtime participates in the cache key.
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling

    path = Path(path_string)
    with rasterio.open(path) as source:
        scale = min(1.0, 2048 / max(source.width, source.height))
        width = max(1, round(source.width * scale))
        height = max(1, round(source.height * scale))
        mask = source.read(1, out_shape=(height, width), resampling=Resampling.nearest)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    glacier = mask > 0
    rgba[glacier] = (14, 165, 233, 155)
    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _build_year_records() -> list[dict[str, Any]]:
    quality_by_year = {int(row["year"]): row for row in _read_csv("year_quality_scores.csv")}
    area_by_year = {int(row["year"]): row for row in _read_csv("decision_ready_area_timeseries.csv")}
    years = sorted(set(quality_by_year) | set(area_by_year))
    records: list[dict[str, Any]] = []

    for year in years:
        quality = quality_by_year.get(year, {})
        area = area_by_year.get(year, {})
        prediction_dir = PREDICTIONS_DIR / str(year)
        raw_results = _load_json(prediction_dir / "results.json")
        provenance = _load_json(prediction_dir / "provenance.json")

        methods: dict[str, dict[str, Any]] = {}
        for method_name, method_result in raw_results.items():
            if not isinstance(method_result, dict):
                continue
            method = method_name.lower()
            mask_filename = f"{method}_mask.tif"
            methods[method] = {
                "name": method,
                "area_km2": _as_float(method_result.get("area_km2")),
                "glacier_pixels": int(method_result.get("glacier_pixels", 0)),
                "mask_url": _artifact_url(year, mask_filename),
                "artifact_available": (prediction_dir / mask_filename).is_file(),
            }

        reported_methods = [
            method.strip() for method in quality.get("methods_available", "").split(",") if method.strip()
        ]
        source_path = CORE_DIR / quality.get("source_file", "")
        overlay_url = _artifact_url(year, "overlay.png")
        provenance_url = _artifact_url(year, "provenance.json")

        records.append(
            {
                "year": year,
                "sensor": quality.get("sensor") or area.get("sensor", ""),
                "source_flag": quality.get("source_flag") or area.get("source_flag", ""),
                "source_file": quality.get("source_file") or area.get("source_file", ""),
                "source_available": source_path.is_file(),
                "source_size_mb": round(source_path.stat().st_size / 1024**2, 1) if source_path.is_file() else None,
                "quality_score": int(_as_float(quality.get("quality_score"))),
                "confidence": quality.get("confidence", "unknown"),
                "include_in_strict_trend": _as_bool(quality.get("include_in_strict_trend")),
                "caveat": quality.get("caveat") or area.get("caveat", ""),
                "primary_method": area.get("primary_method", ""),
                "primary_area_km2": _as_float(area.get("area_km2")),
                "reported_methods": reported_methods,
                "artifact_methods": sorted(methods),
                "methods": methods,
                "overlay_url": overlay_url,
                "provenance_url": provenance_url,
                "provenance_available": bool(provenance),
                "artifact_status": "ready" if overlay_url and methods else "metadata_only",
            }
        )
    return records


@router.get("", summary="List locally available analysis years")
def list_years(strict_only: bool = Query(False)) -> dict[str, Any]:
    records = _build_year_records()
    if strict_only:
        records = [record for record in records if record["include_in_strict_trend"]]
    return {
        "years": records,
        "total": len(records),
        "strict_only": strict_only,
        "source": "local verified tables and on-disk prediction artifacts",
    }


@router.get("/compare", summary="Compare two precomputed local years")
def compare_years(from_year: int = Query(...), to_year: int = Query(...)) -> dict[str, Any]:
    records = {record["year"]: record for record in _build_year_records()}
    missing = [year for year in (from_year, to_year) if year not in records]
    if missing:
        raise HTTPException(404, f"No local result metadata for year(s): {missing}")
    before = records[from_year]
    after = records[to_year]
    change = after["primary_area_km2"] - before["primary_area_km2"]
    change_percent = change / before["primary_area_km2"] * 100 if before["primary_area_km2"] else None
    comparable = bool(before["include_in_strict_trend"] and after["include_in_strict_trend"])
    warnings = [record["caveat"] for record in (before, after) if record["caveat"]]
    if before["sensor"] != after["sensor"]:
        warnings.append(f"Cross-sensor comparison: {before['sensor']} versus {after['sensor']}.")
    return {
        "from": before,
        "to": after,
        "change_km2": round(change, 2),
        "change_percent": round(change_percent, 2) if change_percent is not None else None,
        "comparable_in_strict_trend": comparable,
        "warnings": warnings,
        "method": "decision-ready primary area table",
    }


@router.get("/{year}/map-layer", summary="Get georeferencing for a yearly segmentation layer")
def map_layer_metadata(year: int) -> dict[str, Any]:
    return _map_layer_metadata(year)


@router.get("/{year}/map-layer.png", summary="Render a transparent yearly segmentation map layer")
def map_layer_image(year: int) -> Response:
    path, _ = _map_mask(year)
    content = _render_map_layer(str(path), path.stat().st_mtime_ns)
    return Response(
        content,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{year}", summary="Inspect one precomputed local year")
def get_year(year: int) -> dict[str, Any]:
    record = next((item for item in _build_year_records() if item["year"] == year), None)
    if record is None:
        raise HTTPException(404, f"No local result metadata for year {year}")
    return record
