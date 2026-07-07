"""GlacierNET-KZ MCP Server.

Exposes glacier satellite data and predictions as MCP tools + resources
that any AI model (OpenRouter, Claude, Cursor, etc.) can query in real-time.

Usage:
    python server.py              # stdio mode (for Claude Code, Cursor, etc.)
    python server.py --sse        # SSE mode (for remote access)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from mcp.server.fastmcp import FastMCP
from rasterio.warp import transform as warp_transform

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SENTINEL2_DIR = PROJECT_ROOT / "data" / "raw" / "sentinel2"
LANDSAT_DIR = PROJECT_ROOT / "data" / "raw" / "landsat"
PREDICTIONS_DIR = PROJECT_ROOT / "predictions"
RGI_DIR = PROJECT_ROOT / "data" / "rgi"
MASKS_DIR = PROJECT_ROOT / "data" / "processed" / "masks"
THUMBNAILS_DIR = PROJECT_ROOT / "predictions" / "_thumbnails"
RESULTS_DIR = PROJECT_ROOT / "results"
TABLES_DIR = RESULTS_DIR / "tables"

S2_BANDS = ["B2", "B3", "B4", "B8", "B8A", "B11", "B12"]
LSAT_BANDS = ["B2", "B3", "B4", "B8", "B11"]
INDEX_NAMES = ["NDSI", "NDWI", "BSI", "EVI"]
S2_SCALE = 10000.0

mcp = FastMCP(
    "GlacierNET-KZ",
    instructions=(
        "Glacier satellite data and predictions API for Zailiyskiy Alatau, Kazakhstan. "
        "Use describe_map_year(year) to get a full analysis of any year's map. "
        "Use get_database_summary() to browse the entire database. "
        "Use compare_years(y1,y2) to compare glacier changes."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _discover_sources() -> dict[str, dict[str, Path]]:
    """Scan data directories and return {source: {year: path}}."""
    sources: dict[str, dict[str, Path]] = {"sentinel2": {}, "landsat": {}}
    for src_dir, src_name in [(SENTINEL2_DIR, "sentinel2"), (LANDSAT_DIR, "landsat")]:
        if src_dir.is_dir():
            for f in sorted(src_dir.iterdir()):
                if f.suffix.lower() in (".tif", ".tiff"):
                    parts = f.stem.split("_")
                    if len(parts) == 2 and parts[1].isdigit():
                        sources[src_name][int(parts[1])] = f
    return sources


def _discover_predictions() -> dict[int, dict[str, Any]]:
    """Scan predictions/ directory and return {year: {models, masks}}."""
    result: dict[int, dict[str, Any]] = {}
    if not PREDICTIONS_DIR.is_dir():
        return result
    for p_dir in sorted(PREDICTIONS_DIR.iterdir()):
        if not p_dir.is_dir() or not p_dir.name.isdigit():
            continue
        year = int(p_dir.name)
        result[year] = {"models": {}, "available_masks": []}
        results_file = p_dir / "results.json"
        if results_file.exists():
            try:
                result[year]["models"] = json.loads(results_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        for f in p_dir.iterdir():
            if f.suffix.lower() in (".tif", ".tiff"):
                model = f.stem.replace("_mask", "")
                result[year]["available_masks"].append(model)
    return result


def _get_source(year: int) -> tuple[str, Path] | None:
    """Return (source_name, path) for a year, or None."""
    sources = _discover_sources()
    for s in ["sentinel2", "landsat"]:
        if year in sources[s]:
            return s, sources[s][year]
    return None


def _read_json_file(path: Path) -> dict[str, Any] | list[Any]:
    """Read a project JSON artifact and return a structured error on failure."""
    if not path.exists():
        return {"error": f"File not found: {path.relative_to(PROJECT_ROOT)}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON in {path.relative_to(PROJECT_ROOT)}: {exc}"}


def _band_names(source: str, n_bands: int) -> list[str]:
    """Return human-readable band names for a given source and band count."""
    reflect = LSAT_BANDS if source == "landsat" else S2_BANDS
    names = list(reflect)
    remaining = n_bands - len(reflect)
    for i in range(remaining):
        if i < len(INDEX_NAMES):
            names.append(INDEX_NAMES[i])
        else:
            names.append(f"Band_{len(reflect) + i}")
    return names


def _load_image(year: int) -> tuple[np.ndarray, str, rasterio.DatasetReader] | None:
    """Load full image array + source name + open dataset. Caller must close dataset."""
    info = _get_source(year)
    if info is None:
        return None
    src_name, path = info
    ds = rasterio.open(path)
    img = ds.read().astype(np.float32)
    return img, src_name, ds


def _classify_pixels(img: np.ndarray, src_name: str) -> dict[str, Any]:
    """Classify terrain zones from spectral indices. Returns pixel counts + area."""
    n_reflect = len(S2_BANDS) if src_name == "sentinel2" else len(LSAT_BANDS)
    n_bands = img.shape[0]

    # Find index bands
    ndsi_idx = None
    ndwi_idx = None
    bsi_idx = None
    evi_idx = None
    band_names = _band_names(src_name, n_bands)
    for i, name in enumerate(band_names):
        if name == "NDSI":
            ndsi_idx = i
        elif name == "NDWI":
            ndwi_idx = i
        elif name == "BSI":
            bsi_idx = i
        elif name == "EVI":
            evi_idx = i

    h, w = img.shape[1], img.shape[2]
    total_pixels = h * w

    # Build valid mask (non-nan, non-zero across most bands)
    valid = np.isfinite(img).all(axis=0)
    if valid.sum() == 0:
        return {"total": total_pixels, "valid": 0, "zones": {}}

    # Spectral classification using indices
    zones: dict[str, int] = {}

    if ndsi_idx is not None:
        ndsi = img[ndsi_idx]
        snow_ice = np.sum(valid & (ndsi > 0.4))
        debris_ice = np.sum(valid & (ndsi > 0.1) & (ndsi <= 0.4))
        zones["snow_ice"] = int(snow_ice)
        zones["debris_ice"] = int(debris_ice)
    else:
        # Fallback: use B4/B11 ratio if available
        if n_reflect >= 5:
            b4 = img[2] if n_bands > 2 else None
            b11 = img[4] if n_bands > 4 else None
            if b4 is not None and b11 is not None:
                ratio = np.where((b4 + b11) > 0, (b4 - b11) / (b4 + b11), 0)
                zones["snow_ice"] = int(np.sum(valid & (ratio > 0.4)))
                zones["debris_ice"] = int(np.sum(valid & (ratio > 0.1) & (ratio <= 0.4)))

    if ndwi_idx is not None:
        ndwi = img[ndwi_idx]
        water = np.sum(valid & (ndwi > 0.3))
        zones["water"] = int(water)

    if bsi_idx is not None:
        bsi = img[bsi_idx]
        bare_rock = np.sum(valid & (bsi > 0.1))
        zones["bare_rock"] = int(bare_rock)
    elif n_reflect >= 5:
        # Estimate bare soil from BSI-like ratio
        b3 = img[1] if n_bands > 1 else None
        b11 = img[4] if n_bands > 4 else None
        if b3 is not None and b11 is not None:
            ratio = np.where((b3 + b11) > 0, (b3 - b11) / (b3 + b11), 0)
            zones["bare_rock"] = int(np.sum(valid & (ratio > 0.1)))

    if evi_idx is not None:
        evi = img[evi_idx]
        vegetation = np.sum(valid & (evi > 0.2))
        zones["vegetation"] = int(vegetation)

    # Remaining valid pixels = unclassified terrain
    classified = sum(zones.get(k, 0) for k in ["snow_ice", "debris_ice", "water", "bare_rock", "vegetation"])
    zones["other_terrain"] = int(max(0, valid.sum() - classified))

    resolution_m = 10.0  # default
    pixel_area_m2 = resolution_m * resolution_m

    return {
        "total": total_pixels,
        "valid": int(valid.sum()),
        "zones": {
            name: {
                "pixels": count,
                "area_km2": round(count * pixel_area_m2 / 1e6, 3),
                "fraction_pct": round(count / max(valid.sum(), 1) * 100, 2),
            }
            for name, count in sorted(zones.items(), key=lambda x: -x[1])
            if count > 0
        },
    }


# ---------------------------------------------------------------------------
# ORIGINAL TOOLS (kept for backward compat)
# ---------------------------------------------------------------------------

@mcp.tool()
def list_data_years() -> str:
    """List all available satellite data years per source (Sentinel-2 vs Landsat)."""
    sources = _discover_sources()
    lines = ["## Available Satellite Data\n"]
    for src in ["sentinel2", "landsat"]:
        years = sorted(sources[src].keys())
        lines.append(f"**{src.capitalize()}:** {len(years)} year(s) — {', '.join(str(y) for y in years)}")
        for y in years:
            size_mb = sources[src][y].stat().st_size / (1024 * 1024)
            lines.append(f"  - {y}: {size_mb:.0f} MB")
    return "\n".join(lines)


@mcp.tool()
def list_predictions() -> str:
    """List all pre-computed glacier predictions with area statistics."""
    preds = _discover_predictions()
    if not preds:
        return "No predictions found. Run `python predict.py --year ...` first."
    lines = ["## Glacier Predictions\n"]
    for year in sorted(preds.keys()):
        p = preds[year]
        lines.append(f"**{year}:**")
        for model, stats in p.get("models", {}).items():
            area = stats.get("area_km2", "?")
            lines.append(f"  - {model}: {area} km²")
        if p["available_masks"]:
            lines.append(f"  - Masks available: {', '.join(p['available_masks'])}")
    return "\n".join(lines)


@mcp.tool()
def get_image_metadata(year: int) -> str:
    """Get metadata for a satellite image year: size, CRS, resolution, band count."""
    info = _get_source(year)
    if info is None:
        sources = _discover_sources()
        return f"Year {year} not found. Available: {json.dumps({s: list(k.keys()) for s, k in sources.items()}, ensure_ascii=False)}"
    src_name, path = info
    with rasterio.open(path) as src_r:
        meta = {
            "source": src_name,
            "year": year,
            "width": src_r.width,
            "height": src_r.height,
            "pixels": src_r.width * src_r.height,
            "crs": str(src_r.crs),
            "resolution_m": abs(src_r.res[0]),
            "bands": src_r.count,
            "band_names": _band_names(src_name, src_r.count),
            "bounds": list(src_r.bounds),
            "file_size_mb": round(path.stat().st_size / (1024 * 1024), 1),
        }
    return json.dumps(meta, indent=2, ensure_ascii=False)


@mcp.tool()
def get_glacier_area(year: int, model: str = "ndsi") -> str:
    """Get pre-computed glacier area for a given year and model (ndsi, rf, etc.)."""
    preds = _discover_predictions()
    if year not in preds:
        return (f"Year {year} has no predictions yet. "
                f"Available: {sorted(preds.keys())}. "
                f"Run `python predict.py --year {year} --models ndsi rf` to generate.")
    p = preds[year]
    if model in p.get("models", {}):
        stats = p["models"][model]
        lines = [
            f"## {year} — {model}\n",
            f"**Glacier area:** {stats['area_km2']:.2f} km²",
            f"**Glacier pixels:** {stats['glacier_pixels']:,}",
            f"**Total pixels:** {stats['total_pixels']:,}",
            f"**Glacier fraction:** {stats['glacier_pixels'] / stats['total_pixels'] * 100:.2f}%",
        ]
        return "\n".join(lines)
    available = list(p.get("models", {}).keys())
    return f"Model '{model}' not found for {year}. Available: {available or '(masks only: ' + str(p['available_masks']) + ')'}"


@mcp.tool()
def get_all_glacier_areas() -> str:
    """Get glacier area for ALL years with predictions, all models."""
    preds = _discover_predictions()
    if not preds:
        return "No predictions found."
    lines = ["## All Glacier Areas\n", "| Year | Source | Model | Area (km²) |", "|------|--------|-------|-----------|"]
    sources = _discover_sources()
    for year in sorted(preds.keys()):
        src_name = "landsat" if year in sources.get("landsat", {}) else "sentinel2" if year in sources.get("sentinel2", {}) else "?"
        p = preds[year]
        if p.get("models"):
            for model, stats in p["models"].items():
                lines.append(f"| {year} | {src_name} | {model} | {stats['area_km2']:.2f} |")
        elif p.get("available_masks"):
            for m in p["available_masks"]:
                lines.append(f"| {year} | {src_name} | {m} | (no area data) |")
    return "\n".join(lines)


@mcp.tool()
def get_band_statistics(year: int) -> str:
    """Get per-band statistics (mean, std, min, max) for a satellite image year."""
    info = _get_source(year)
    if info is None:
        return f"Year {year} not found."
    src_name, path = info
    with rasterio.open(path) as src_rs:
        img = src_rs.read().astype(np.float32)
        n_bands = img.shape[0]
    lines = [f"## Band Statistics — {year} ({src_name})\n"]
    lines.append("| Band | Mean | Std | Min | Max |")
    lines.append("|------|------|-----|-----|-----|")
    band_names = _band_names(src_name, n_bands)
    for i in range(n_bands):
        band = img[i]
        valid = band[np.isfinite(band) & (band != 0)]
        if len(valid) == 0:
            valid = band[np.isfinite(band)]
        if len(valid) == 0:
            lines.append(f"| {band_names[i]} | — | — | — | — |")
            continue
        lines.append(f"| {band_names[i]} | {valid.mean():.2f} | {valid.std():.2f} | {valid.min():.2f} | {valid.max():.2f} |")
    n_reflectance = len(S2_BANDS) if src_name == "sentinel2" else len(LSAT_BANDS)
    if n_bands > n_reflectance:
        lines.append(f"\nBands 1–{n_reflectance} = reflectance (×{S2_SCALE:.0f} scale)")
        lines.append(f"Bands {n_reflectance + 1}–{n_bands} = spectral indices (natural scale)")
    return "\n".join(lines)


@mcp.tool()
def query_pixel(year: int, longitude: float, latitude: float) -> str:
    """Get spectral signature (all bands and indices) for a single geographic coordinate."""
    info = _get_source(year)
    if info is None:
        return f"Year {year} not found."
    src_name, path = info
    try:
        with rasterio.open(path) as src_rs:
            src_crs = src_rs.crs
            if src_crs and src_crs.to_string() != "EPSG:4326":
                xs, ys = warp_transform("EPSG:4326", src_crs, [longitude], [latitude])
                row, col = src_rs.index(xs[0], ys[0])
            else:
                row, col = src_rs.index(longitude, latitude)
            if not (0 <= row < src_rs.height and 0 <= col < src_rs.width):
                return f"Coordinates ({longitude:.4f}, {latitude:.4f}) are outside the image bounds."
            n_bands = src_rs.count
            pixel = src_rs.read(window=((row, row + 1), (col, col + 1)))
            pixel = pixel[:, 0, 0].astype(np.float32)
    except Exception as e:
        return f"Error reading pixel at ({longitude:.4f}, {latitude:.4f}): {e}"
    n_reflectance = len(S2_BANDS) if src_name == "sentinel2" else len(LSAT_BANDS)
    lines = [f"## Pixel at ({longitude:.4f}, {latitude:.4f}) — {year} ({src_name})\n"]
    lines.append(f"**Row:** {row}, **Col:** {col}\n")
    lines.append("| Band | Value | Description |")
    lines.append("|------|-------|-------------|")
    band_names = _band_names(src_name, n_bands)
    for i in range(n_bands):
        val = pixel[i]
        val_str = f"{val:.2f}" if np.isfinite(val) else "NaN"
        if i < n_reflectance:
            norm = val / S2_SCALE if val > 0 else 0
            desc = f"reflectance band (normalized: {norm:.4f})"
        else:
            desc = "spectral index (natural scale)"
        lines.append(f"| {band_names[i]} | {val_str} | {desc} |")
    return "\n".join(lines)


@mcp.tool()
def get_study_area_info() -> str:
    """Get information about the glacier study area: bounding box, target glaciers, elevation context."""
    info = {
        "region": "Zailiyskiy Alatau (Заилийский Алатау), Kazakhstan",
        "basins": ["Malaya Almatinka", "Bolshaya Almatinka"],
        "bounding_box": {"min_lon": 76.5, "min_lat": 42.8, "max_lon": 77.5, "max_lat": 43.2},
        "area_pixels": 44871924,
        "approx_area_km2": 4487,
        "utm_zone": "EPSG:32642 (UTM zone 42N)",
        "resolution_m": 10,
        "target_glaciers": [
            {"id": "tuyuksu", "name": "Туюксу", "lat": 43.0506, "lon": 77.0784,
             "rgi_id": "RGI2000-v7.0-G-13-33843", "priority": 1,
             "notes": "WGMS reference glacier, observations since 1957"},
            {"id": "bogdanovich", "name": "Богдановича", "lat": 43.0394, "lon": 77.0539,
             "rgi_id": "RGI2000-v7.0-G-13-33845", "priority": 2},
            {"id": "mutny", "name": "Мутный", "lat": 45.0, "lon": 80.0, "priority": 3},
        ],
        "data_sources": {
            "sentinel2": {"years": "2015-2024", "bands": S2_BANDS, "indices": INDEX_NAMES},
            "landsat": {"years": "2000-2013", "bands": LSAT_BANDS, "indices": INDEX_NAMES},
        },
    }
    return json.dumps(info, indent=2, ensure_ascii=False)


@mcp.tool()
def get_available_models() -> str:
    """List available models and their status (trained, predicted, etc.)."""
    preds = _discover_predictions()
    models_info = {
        "ndsi": {"type": "threshold", "description": "NDSI threshold (B3-B11)/(B3+B11) > 0.4",
                 "trained": False, "ready": True, "years_predicted": []},
        "rf": {"type": "random_forest", "description": "RandomForestClassifier, 11 spectral features",
               "trained": True, "model_path": str(PROJECT_ROOT / "models" / "random_forest.pkl"),
               "ready": True, "years_predicted": []},
        "unet": {"type": "deep_learning", "description": "U-Net, 4-level encoder-decoder, 256x256",
                 "trained": True, "model_path": str(PROJECT_ROOT / "models" / "unet_best.h5"),
                 "ready": True, "years_predicted": []},
        "attention_unet": {"type": "deep_learning", "description": "Attention U-Net with attention gates",
                           "trained": False, "model_path": "(missing)", "ready": False, "years_predicted": []},
    }
    for year, p in preds.items():
        for model in p.get("models", {}):
            if model in models_info:
                models_info[model]["years_predicted"].append(year)
    return json.dumps(models_info, indent=2, ensure_ascii=False)


@mcp.tool()
def get_glacier_time_series() -> str:
    """Get full time series of glacier areas across all years and models."""
    preds = _discover_predictions()
    if not preds:
        return "No predictions found."
    lines = ["## Glacier Area Time Series\n"]
    lines.append("| Year | Source | NDSI (km²) | RF (km²) | Best (km²) |")
    lines.append("|------|--------|-----------|----------|------------|")
    sources = _discover_sources()
    for year in sorted(preds.keys()):
        p = preds[year]
        ndsi = p.get("models", {}).get("ndsi", {}).get("area_km2")
        rf = p.get("models", {}).get("rf", {}).get("area_km2")
        best = rf if rf else ndsi
        src_name = "landsat" if year in sources.get("landsat", {}) else "S2"
        ndsi_str = f"{ndsi:.2f}" if ndsi else "—"
        rf_str = f"{rf:.2f}" if rf else "—"
        best_str = f"{best:.2f}" if best else "—"
        lines.append(f"| {year} | {src_name} | {ndsi_str} | {rf_str} | {best_str} |")
    lines.append("\n*RF is preferred over NDSI where available (ML-based).*")
    return "\n".join(lines)


@mcp.tool()
def get_pipeline_status() -> str:
    """Return latest pipeline status: raw data, missing years, patches, predictions."""
    return json.dumps(_read_json_file(RESULTS_DIR / "pipeline_status.json"), indent=2, ensure_ascii=False)


@mcp.tool()
def get_data_quality_report() -> str:
    """Return latest data quality gate report, including warnings and errors."""
    return json.dumps(_read_json_file(RESULTS_DIR / "data_quality_report.json"), indent=2, ensure_ascii=False)


@mcp.tool()
def get_data_inventory(limit: int = 20) -> str:
    """Return compact local raster inventory with metadata and provenance hashes."""
    inventory = _read_json_file(RESULTS_DIR / "data_inventory.json")
    if isinstance(inventory, list):
        return json.dumps({"total": len(inventory), "rasters": inventory[: max(0, limit)]}, indent=2, ensure_ascii=False)
    if isinstance(inventory, dict) and isinstance(inventory.get("rasters"), list):
        limited = {**inventory, "rasters": inventory["rasters"][: max(0, limit)]}
        limited["total"] = len(inventory["rasters"])
        return json.dumps(limited, indent=2, ensure_ascii=False)
    return json.dumps(inventory, indent=2, ensure_ascii=False)


@mcp.tool()
def get_decision_readiness() -> str:
    """Return decision-facing time series, year quality scores and strict trend summary."""
    import csv

    summary = _read_json_file(RESULTS_DIR / "decision_readiness_summary.json")
    ts_path = TABLES_DIR / "decision_ready_area_timeseries.csv"
    quality_path = TABLES_DIR / "year_quality_scores.csv"
    timeseries: list[dict[str, str]] = []
    year_quality: list[dict[str, str]] = []
    if ts_path.exists():
        with ts_path.open(encoding="utf-8") as f:
            timeseries = list(csv.DictReader(f))
    if quality_path.exists():
        with quality_path.open(encoding="utf-8") as f:
            year_quality = list(csv.DictReader(f))
    return json.dumps(
        {"summary": summary, "timeseries": timeseries, "year_quality": year_quality},
        indent=2,
        ensure_ascii=False,
    )


# ===========================================================================
# NEW TOOLS — Real-time map analysis
# ===========================================================================

@mcp.tool()
def describe_map_year(year: int, detail: str = "full") -> str:
    """Get a COMPLETE detailed description of a single year's satellite map.

    Reads the actual raster data in real-time and returns:
    - Spatial extent and CRS
    - Band composition and spectral characteristics
    - Per-band statistics (mean, std, min, max, percentiles)
    - Terrain zone classification (snow/ice, debris, rock, water, vegetation)
    - Glacier area from predictions (if available)
    - Data quality assessment (cloud-free pixels, valid coverage)
    - Summary narrative suitable for publication

    Args:
        year: Year to describe (2000-2024)
        detail: "full" for complete analysis, "quick" for essential stats only
    """
    result = _load_image(year)
    if result is None:
        sources = _discover_sources()
        avail = sorted(set(list(sources["sentinel2"].keys()) + list(sources["landsat"].keys())))
        return f"Year {year} not found in database. Available years: {avail}"

    img, src_name, ds = result
    try:
        n_bands, h, w = img.shape
        n_reflect = len(S2_BANDS) if src_name == "sentinel2" else len(LSAT_BANDS)
        band_names = _band_names(src_name, n_bands)

        # --- Spatial info ---
        bounds = ds.bounds
        crs = str(ds.crs)
        res = abs(ds.res[0])

        # Convert bounds to lat/lng if needed
        try:
            if crs != "EPSG:4326":
                lngs, lats = warp_transform(crs, "EPSG:4326",
                                            [bounds.left, bounds.right],
                                            [bounds.bottom, bounds.top])
                bbox_4326 = {"west": min(lngs), "south": min(lats),
                             "east": max(lngs), "north": max(lats)}
            else:
                bbox_4326 = {"west": bounds.left, "south": bounds.bottom,
                             "east": bounds.right, "north": bounds.top}
        except Exception:
            bbox_4326 = {"note": "CRS conversion unavailable"}

        # --- Band statistics ---
        band_stats = []
        for i in range(n_bands):
            band = img[i]
            valid = band[np.isfinite(band) & (band != 0)]
            if len(valid) == 0:
                valid = band[np.isfinite(band)]
            if len(valid) == 0:
                band_stats.append({"name": band_names[i], "status": "empty"})
                continue
            pcts = np.percentile(valid, [5, 25, 50, 75, 95])
            band_stats.append({
                "name": band_names[i],
                "type": "reflectance" if i < n_reflect else "index",
                "mean": round(float(valid.mean()), 2),
                "std": round(float(valid.std()), 2),
                "min": round(float(valid.min()), 2),
                "max": round(float(valid.max()), 2),
                "p5": round(float(pcts[0]), 2),
                "p25": round(float(pcts[1]), 2),
                "median": round(float(pcts[2]), 2),
                "p75": round(float(pcts[3]), 2),
                "p95": round(float(pcts[4]), 2),
                "valid_pixels": int(len(valid)),
            })

        # --- Terrain classification ---
        terrain = _classify_pixels(img, src_name)

        # --- Glacier predictions ---
        preds = _discover_predictions()
        glacier_info = None
        if year in preds:
            p = preds[year]
            if p.get("models"):
                glacier_info = p["models"]

        # --- Data quality ---
        valid_mask = np.isfinite(img).all(axis=0)
        total_px = h * w
        valid_px = int(valid_mask.sum())
        zero_mask = (img[:n_reflect] == 0).all(axis=0) if n_bands >= n_reflect else np.zeros((h, w), dtype=bool)
        zero_px = int(zero_mask.sum())

        quality = {
            "total_pixels": total_px,
            "valid_pixels": valid_px,
            "valid_pct": round(valid_px / max(total_px, 1) * 100, 1),
            "zero_pixels": zero_px,
            "zero_pct": round(zero_px / max(total_px, 1) * 100, 1),
        }

        # --- Build output ---
        lines = [f"# Full Map Description — {year} ({src_name.upper()})\n"]

        lines.append("## Spatial Coverage")
        lines.append("- **Source:** Sentinel-2 MSI" if src_name == "sentinel2" else "- **Source:** Landsat (OLI/TM)")
        lines.append(f"- **CRS:** {crs}")
        lines.append(f"- **Resolution:** {res}m")
        lines.append(f"- **Dimensions:** {w} × {h} pixels ({total_px:,} total)")
        lines.append(f"- **Bounding box (WGS84):** {json.dumps(bbox_4326)}")
        lines.append(f"- **Approx area:** {round(total_px * res * res / 1e6, 1)} km²")
        lines.append(f"- **File size:** {Path(ds.name).stat().st_size / (1024*1024):.0f} MB")
        lines.append("")

        if detail == "full":
            lines.append("## Spectral Bands")
            lines.append("| Band | Type | Mean | Std | Min | P5 | Median | P95 | Max | Valid px |")
            lines.append("|------|------|------|-----|-----|-----|--------|-----|-----|----------|")
            for s in band_stats:
                if "status" in s:
                    lines.append(f"| {s['name']} | — | — | — | — | — | — | — | — | — |")
                else:
                    lines.append(
                        f"| {s['name']} | {s['type']} | {s['mean']} | {s['std']} | "
                        f"{s['min']} | {s['p5']} | {s['median']} | {s['p95']} | {s['max']} | {s['valid_pixels']:,} |"
                    )
            lines.append("")

        lines.append("## Terrain Zone Classification")
        if terrain.get("zones"):
            lines.append("| Zone | Pixels | Area (km²) | Coverage |")
            lines.append("|------|--------|------------|----------|")
            for zone_name, zdata in terrain["zones"].items():
                label = zone_name.replace("_", " ").title()
                lines.append(f"| {label} | {zdata['pixels']:,} | {zdata['area_km2']:.3f} | {zdata['fraction_pct']:.1f}% |")
            lines.append(f"\n*Valid pixels analyzed: {terrain['valid']:,} / {terrain['total']:,}*")
        else:
            lines.append("Insufficient spectral indices for classification.")
        lines.append("")

        if glacier_info:
            lines.append("## Glacier Predictions")
            lines.append("| Model | Area (km²) | Glacier Pixels | Fraction |")
            lines.append("|-------|------------|----------------|----------|")
            for model, stats in glacier_info.items():
                area = stats.get("area_km2", "?")
                px = stats.get("glacier_pixels", "?")
                frac = round(stats.get("glacier_pixels", 0) / max(stats.get("total_pixels", 1), 1) * 100, 2)
                lines.append(f"| {model} | {area} | {px:,} | {frac}% |")
        else:
            lines.append("## Glacier Predictions\n*No predictions available for this year.*")
        lines.append("")

        lines.append("## Data Quality")
        lines.append(f"- Valid pixels: {quality['valid_pixels']:,} / {quality['total_pixels']:,} ({quality['valid_pct']}%)")
        lines.append(f"- Zero-value pixels: {quality['zero_pixels']:,} ({quality['zero_pct']}%)")
        lines.append(f"- Coverage assessment: {'Good' if quality['valid_pct'] > 80 else 'Partial' if quality['valid_pct'] > 50 else 'Limited'}")
        lines.append("")

        # Narrative
        lines.append("## Summary")
        glacier_str = ""
        if glacier_info:
            best_model = list(glacier_info.keys())[0]
            area = glacier_info[best_model].get("area_km2", "unknown")
            glacier_str = f" Glacier area estimated at {area} km²."
        lines.append(
            f"Satellite image from {year} over Zailiyskiy Alatau, Kazakhstan, "
            f"acquired by {'Sentinel-2 MSI' if src_name == 'sentinel2' else 'Landsat'} "
            f"at {res}m resolution. The scene covers approximately "
            f"{round(total_px * res * res / 1e6, 1)} km² with {quality['valid_pct']}% valid pixel coverage.{glacier_str}"
        )

        return "\n".join(lines)
    finally:
        ds.close()


@mcp.tool()
def get_database_summary() -> str:
    """Browse the ENTIRE database at once — all sources, years, predictions, models.

    Returns a complete catalog of everything available in the system,
    including file sizes, band counts, prediction status, and data quality.
    """
    sources = _discover_sources()
    preds = _discover_predictions()

    lines = ["# Complete Database Summary\n"]

    # --- Overview ---
    all_years = sorted(set(
        list(sources["sentinel2"].keys()) + list(sources["landsat"].keys())
    ))
    pred_years = sorted(preds.keys())
    total_size = sum(
        p.stat().st_size
        for src in sources.values()
        for p in src.values()
    )

    lines.append("## Overview")
    lines.append(f"- **Total years with satellite data:** {len(all_years)}")
    lines.append(f"- **Years with predictions:** {len(pred_years)}")
    lines.append(f"- **Sentinel-2 images:** {len(sources['sentinel2'])}")
    lines.append(f"- **Landsat images:** {len(sources['landsat'])}")
    lines.append(f"- **Total data size:** {total_size / (1024**3):.2f} GB")
    lines.append(f"- **Date range:** {all_years[0] if all_years else '?'} – {all_years[-1] if all_years else '?'}")
    lines.append("")

    # --- Satellite Data Catalog ---
    lines.append("## Satellite Data Catalog\n")
    lines.append("| Year | Source | Bands | Resolution | File Size | Status |")
    lines.append("|------|--------|-------|------------|-----------|--------|")
    for src_name in ["sentinel2", "landsat"]:
        for year in sorted(sources[src_name].keys()):
            path = sources[src_name][year]
            size_mb = path.stat().st_size / (1024 * 1024)
            try:
                with rasterio.open(path) as ds:
                    nb = ds.count
                    res_m = abs(ds.res[0])
            except Exception:
                nb = "?"
                res_m = "?"
            pred_status = "✅ Predicted" if year in preds else "⏳ Pending"
            lines.append(f"| {year} | {src_name} | {nb} | {res_m}m | {size_mb:.0f} MB | {pred_status} |")
    lines.append("")

    # --- Predictions Catalog ---
    lines.append("## Predictions Catalog\n")
    if preds:
        lines.append("| Year | Model | Area (km²) | Glacier Pixels | Mask File |")
        lines.append("|------|-------|------------|----------------|-----------|")
        for year in pred_years:
            p = preds[year]
            if p.get("models"):
                for model, stats in p["models"].items():
                    area = stats.get("area_km2", "?")
                    px = stats.get("glacier_pixels", "?")
                    mask_file = f"predictions/{year}/{model}_mask.tif"
                    lines.append(f"| {year} | {model} | {area} | {px:,} | {mask_file} |")
            if p.get("available_masks") and not p.get("models"):
                for m in p["available_masks"]:
                    lines.append(f"| {year} | {m} | — | — | predictions/{year}/{m}_mask.tif |")
    else:
        lines.append("*No predictions found.*")
    lines.append("")

    # --- Models ---
    lines.append("## Available Models\n")
    lines.append("| Model | Type | Status | Years Predicted |")
    lines.append("|-------|------|--------|-----------------|")
    model_status = {
        "ndsi": ("threshold", "Ready"),
        "rf": ("random_forest", "Trained"),
        "unet": ("deep_learning", "Trained"),
        "attention_unet": ("deep_learning", "Not trained"),
    }
    for model_name, (mtype, status) in model_status.items():
        yrs = [str(y) for y in pred_years if model_name in preds.get(y, {}).get("models", {})]
        lines.append(f"| {model_name} | {mtype} | {status} | {', '.join(yrs) if yrs else '—'} |")
    lines.append("")

    # --- File System ---
    lines.append("## File System\n")
    for subdir, label in [("data/raw/sentinel2", "Sentinel-2 raw"),
                          ("data/raw/landsat", "Landsat raw"),
                          ("predictions", "Predictions"),
                          ("data/rgi", "RGI shapefiles"),
                          ("data/processed/masks", "Processed masks"),
                          ("models", "Trained models")]:
        full = PROJECT_ROOT / subdir
        if full.is_dir():
            files = list(full.iterdir())
            total = sum(f.stat().st_size for f in files if f.is_file())
            lines.append(f"- **{label}** (`{subdir}/`): {len(files)} files, {total / (1024*1024):.0f} MB")
        else:
            lines.append(f"- **{label}** (`{subdir}/`): not found")
    lines.append("")

    # --- Study Area ---
    lines.append("## Study Area")
    lines.append("- **Region:** Zailiyskiy Alatau, Kazakhstan (76.5–77.5°E, 42.8–43.2°N)")
    lines.append("- **Area:** ~4,487 km²")
    lines.append("- **Key glaciers:** Туюксу (WGMS reference), Богдановича, Мутный")
    lines.append("- **Data span:** 2000–2024 (Landsat → Sentinel-2 transition ~2015)")

    return "\n".join(lines)


@mcp.tool()
def compare_years(year1: int, year2: int) -> str:
    """Compare two years side-by-side: glacier area change, spectral differences, retreat/advance.

    Reads actual raster data from both years and computes:
    - Glacier area difference (km² and %)
    - Spectral band comparison
    - Terrain zone changes
    - Retreat/advance interpretation
    """
    r1 = _load_image(year1)
    r2 = _load_image(year2)

    if r1 is None and r2 is None:
        return f"Neither {year1} nor {year2} found in database."
    if r1 is None:
        return f"Year {year1} not found. Cannot compare."
    if r2 is None:
        return f"Year {year2} not found. Cannot compare."

    img1, src1, ds1 = r1
    img2, src2, ds2 = r2

    try:
        lines = [f"# Comparison: {year1} vs {year2}\n"]

        lines.append("## Source Comparison")
        lines.append(f"| | {year1} | {year2} |")
        lines.append("|---|--------|--------|")
        lines.append(f"| Source | {src1} | {src2} |")
        lines.append(f"| Bands | {img1.shape[0]} | {img2.shape[0]} |")
        lines.append(f"| Size | {img1.shape[2]}×{img1.shape[1]} | {img2.shape[2]}×{img2.shape[1]} |")
        lines.append("")

        # Band comparison
        bn1 = _band_names(src1, img1.shape[0])
        bn2 = _band_names(src2, img2.shape[0])
        common = [b for b in bn1 if b in bn2]

        lines.append("## Spectral Comparison (common bands)")
        lines.append("| Band | Mean {} | Mean {} | Δ | Change |".format(year1, year2))
        lines.append("|------|---------|---------|---|--------|")
        for band_name in common:
            i1 = bn1.index(band_name)
            i2 = bn2.index(band_name)
            v1 = img1[i1]
            v2 = img2[i2]
            valid1 = v1[np.isfinite(v1) & (v1 != 0)]
            valid2 = v2[np.isfinite(v2) & (v2 != 0)]
            if len(valid1) == 0 or len(valid2) == 0:
                continue
            m1, m2 = float(valid1.mean()), float(valid2.mean())
            delta = m2 - m1
            pct = (delta / max(abs(m1), 1e-6)) * 100
            arrow = "↑" if pct > 2 else "↓" if pct < -2 else "→"
            lines.append(f"| {band_name} | {m1:.2f} | {m2:.2f} | {delta:+.2f} | {arrow} {abs(pct):.1f}% |")
        lines.append("")

        # Glacier area comparison
        preds = _discover_predictions()
        if year1 in preds and year2 in preds:
            lines.append("## Glacier Area Change")
            lines.append("| Model | {} (km²) | {} (km²) | Δ km² | Δ % |".format(year1, year2))
            lines.append("|-------|---------|---------|-------|-----|")
            for model in set(list(preds[year1].get("models", {}).keys()) +
                           list(preds[year2].get("models", {}).keys())):
                a1 = preds[year1].get("models", {}).get(model, {}).get("area_km2")
                a2 = preds[year2].get("models", {}).get(model, {}).get("area_km2")
                if a1 is not None and a2 is not None:
                    delta_km2 = a2 - a1
                    delta_pct = (delta_km2 / max(a1, 1e-6)) * 100
                    lines.append(f"| {model} | {a1:.2f} | {a2:.2f} | {delta_km2:+.2f} | {delta_pct:+.1f}% |")
                elif a1 is not None:
                    lines.append(f"| {model} | {a1:.2f} | — | — | — |")
                elif a2 is not None:
                    lines.append(f"| {model} | — | {a2:.2f} | — | — |")
            lines.append("")

        # Terrain comparison
        t1 = _classify_pixels(img1, src1)
        t2 = _classify_pixels(img2, src2)
        all_zones = sorted(set(list(t1.get("zones", {}).keys()) + list(t2.get("zones", {}).keys())))
        if all_zones:
            lines.append("## Terrain Zone Changes")
            lines.append("| Zone | {} (km²) | {} (km²) | Δ km² |".format(year1, year2))
            lines.append("|------|---------|---------|-------|")
            for z in all_zones:
                a1 = t1.get("zones", {}).get(z, {}).get("area_km2", 0)
                a2 = t2.get("zones", {}).get(z, {}).get("area_km2", 0)
                delta = a2 - a1
                label = z.replace("_", " ").title()
                lines.append(f"| {label} | {a1:.3f} | {a2:.3f} | {delta:+.3f} |")
            lines.append("")

        # Interpretation
        if year1 in preds and year2 in preds:
            best_model = "rf"
            a1 = preds[year1].get("models", {}).get(best_model, {}).get("area_km2")
            a2 = preds[year2].get("models", {}).get(best_model, {}).get("area_km2")
            if a1 and a2:
                delta = a2 - a1
                lines.append("## Interpretation")
                if delta < -5:
                    lines.append(f"**Significant glacier retreat** of {abs(delta):.2f} km² ({abs(delta/a1*100):.1f}%) between {year1} and {year2}.")
                elif delta > 5:
                    lines.append(f"**Glacier advance** of {delta:.2f} km² ({delta/a1*100:.1f}%) between {year1} and {year2}.")
                else:
                    lines.append(f"**Relatively stable** glacier area ({delta:+.2f} km², {delta/a1*100:+.1f}%) between {year1} and {year2}.")

        return "\n".join(lines)
    finally:
        ds1.close()
        ds2.close()


@mcp.tool()
def analyze_glacier_zones(year: int) -> str:
    """Classify terrain zones for a year: snow/ice, debris-covered ice, rock, water, vegetation.

    Uses spectral indices (NDSI, NDWI, BSI, EVI) to classify each pixel
    and returns area statistics for each terrain type.
    """
    result = _load_image(year)
    if result is None:
        return f"Year {year} not found."
    img, src_name, ds = result
    try:
        terrain = _classify_pixels(img, src_name)
        lines = [f"# Terrain Classification — {year} ({src_name.upper()})\n"]
        if terrain.get("zones"):
            lines.append("| Zone | Pixels | Area (km²) | Coverage (%) | Description |")
            lines.append("|------|--------|------------|--------------|-------------|")
            descriptions = {
                "snow_ice": "Clean snow and glacier ice (NDSI > 0.4)",
                "debris_ice": "Debris-covered glacier ice (0.1 < NDSI ≤ 0.4)",
                "bare_rock": "Exposed rock and soil (BSI > 0.1)",
                "water": "Water bodies including glacial lakes (NDWI > 0.3)",
                "vegetation": "Alpine vegetation (EVI > 0.2)",
                "other_terrain": "Unclassified terrain",
            }
            for zone_name, zdata in terrain["zones"].items():
                label = zone_name.replace("_", " ").title()
                desc = descriptions.get(zone_name, "")
                lines.append(f"| {label} | {zdata['pixels']:,} | {zdata['area_km2']:.3f} | {zdata['fraction_pct']:.1f}% | {desc} |")
            lines.append(f"\n**Total valid pixels:** {terrain['valid']:,} / {terrain['total']:,}")
        else:
            lines.append("Insufficient spectral data for zone classification.")
        return "\n".join(lines)
    finally:
        ds.close()


@mcp.tool()
def export_map_thumbnail(year: int, width: int = 512) -> str:
    """Generate a quick-look RGB thumbnail of a satellite image.

    Returns a base64-encoded PNG image or a file path.
    Uses B4-B3-B2 (true color) for Sentinel-2, B4-B3-B2 for Landsat.
    """
    result = _load_image(year)
    if result is None:
        return f"Year {year} not found."
    img, src_name, ds = result
    try:
        n_bands = img.shape[0]
        h, w_orig = img.shape[1], img.shape[2]

        # Select RGB bands
        if src_name == "sentinel2" and n_bands >= 3:
            # B4(R), B3(G), B2(B)
            r_idx, g_idx, b_idx = 2, 1, 0
        elif src_name == "landsat" and n_bands >= 3:
            # B4(R), B3(G), B2(B)
            r_idx, g_idx, b_idx = 2, 1, 0
        else:
            r_idx, g_idx, b_idx = 0, min(1, n_bands - 1), min(2, n_bands - 1)

        rgb = np.stack([img[r_idx], img[g_idx], img[b_idx]], axis=-1)

        # Normalize to 0-255
        valid = rgb[np.isfinite(rgb)]
        if len(valid) == 0:
            return "No valid data for thumbnail."
        p2, p98 = np.percentile(valid, [2, 98])
        rgb = np.clip((rgb - p2) / max(p98 - p2, 1) * 255, 0, 255).astype(np.uint8)

        # Replace NaN with black
        rgb[~np.isfinite(img[r_idx]) | ~np.isfinite(img[g_idx]) | ~np.isfinite(img[b_idx])] = 0

        # Resize to thumbnail width
        scale = width / w_orig
        new_h = max(1, int(h * scale))
        try:
            from PIL import Image
            pil_img = Image.fromarray(rgb)
            pil_img = pil_img.resize((width, new_h), Image.LANCZOS)

            THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
            out_path = THUMBNAILS_DIR / f"thumb_{year}_{width}px.png"
            pil_img.save(str(out_path), "PNG")
            return f"Thumbnail saved: {out_path}\nSize: {width}×{new_h} pixels\nSource: {src_name} {year}"
        except ImportError:
            # Fallback: save raw RGB as numpy info
            return (
                f"Thumbnail generation requires Pillow (`pip install Pillow`).\n"
                f"Image info: {src_name} {year}, {w_orig}×{h} pixels, "
                f"RGB bands: {r_idx},{g_idx},{b_idx}, value range: [{p2:.0f}, {p98:.0f}]"
            )
    finally:
        ds.close()


@mcp.tool()
def query_pixel_classification(year: int, longitude: float, latitude: float) -> str:
    """Query a specific pixel and classify its terrain type (ice, rock, snow, water, vegetation).

    Combines query_pixel with spectral classification for a single point.
    """
    info = _get_source(year)
    if info is None:
        return f"Year {year} not found."
    src_name, path = info

    try:
        with rasterio.open(path) as src_rs:
            src_crs = src_rs.crs
            if src_crs and src_crs.to_string() != "EPSG:4326":
                xs, ys = warp_transform("EPSG:4326", src_crs, [longitude], [latitude])
                row, col = src_rs.index(xs[0], ys[0])
            else:
                row, col = src_rs.index(longitude, latitude)
            if not (0 <= row < src_rs.height and 0 <= col < src_rs.width):
                return f"Coordinates ({longitude:.4f}, {latitude:.4f}) outside image bounds."

            pixel = src_rs.read(window=((row, row + 1), (col, col + 1)))
            pixel = pixel[:, 0, 0].astype(np.float32)
    except Exception as e:
        return f"Error: {e}"

    n_bands = len(pixel)
    band_names = _band_names(src_name, n_bands)

    # Find indices
    ndsi = ndwi = bsi = evi = None
    for i, name in enumerate(band_names):
        if name == "NDSI" and i < n_bands:
            ndsi = pixel[i]
        elif name == "NDWI" and i < n_bands:
            ndwi = pixel[i]
        elif name == "BSI" and i < n_bands:
            bsi = pixel[i]
        elif name == "EVI" and i < n_bands:
            evi = pixel[i]

    # Classification
    classification = "Unknown"
    confidence = 0.0
    reasons = []

    if ndsi is not None:
        if ndsi > 0.4:
            classification = "Snow/Ice (clean glacier)"
            confidence = min(0.95, 0.5 + ndsi * 0.5)
            reasons.append(f"NDSI={ndsi:.3f} > 0.4")
        elif ndsi > 0.1:
            classification = "Debris-covered ice or wet snow"
            confidence = 0.6 + ndsi
            reasons.append(f"NDSI={ndsi:.3f} (0.1–0.4 range)")
        elif ndwi is not None and ndwi > 0.3:
            classification = "Water body"
            confidence = 0.7 + ndwi * 0.3
            reasons.append(f"NDWI={ndwi:.3f} > 0.3")
        else:
            classification = "Rock/soil/vegetation"
            confidence = 0.5
            reasons.append(f"NDSI={ndsi:.3f} (low)")

    if bsi is not None and bsi > 0.1:
        classification = "Bare rock/soil"
        confidence = 0.6 + bsi * 0.3
        reasons.append(f"BSI={bsi:.3f} > 0.1")

    if evi is not None and evi > 0.2:
        classification = "Vegetation"
        confidence = 0.7 + evi * 0.3
        reasons.append(f"EVI={evi:.3f} > 0.2")

    lines = [f"## Pixel Classification — ({longitude:.4f}, {latitude:.4f}) — {year}\n"]
    lines.append(f"**Classification:** {classification}")
    lines.append(f"**Confidence:** {confidence:.0%}")
    lines.append(f"**Reasons:** {'; '.join(reasons)}\n")
    lines.append("| Band | Value |")
    lines.append("|------|-------|")
    for i in range(n_bands):
        val = pixel[i]
        lines.append(f"| {band_names[i]} | {val:.4f} |")

    return "\n".join(lines)


@mcp.tool()
def search_predictions(query: str = "") -> str:
    """Search predictions by year range, model, or area threshold.

    Examples:
        - search_predictions("2010-2020") — years in range
        - search_predictions("rf") — only RF model
        - search_predictions("area>500") — areas above 500 km²
        - search_predictions("") — all predictions
    """
    preds = _discover_predictions()
    if not preds:
        return "No predictions found."

    results = []
    q = query.lower().strip()

    for year in sorted(preds.keys()):
        p = preds[year]
        for model, stats in p.get("models", {}).items():
            area = stats.get("area_km2", 0)

            # Filter by query
            if q:
                if q.replace("-", "").isdigit():
                    # Year range
                    try:
                        if "-" in q:
                            y1, y2 = q.split("-", 1)
                            if not (int(y1) <= year <= int(y2)):
                                continue
                        elif q not in str(year):
                            continue
                    except ValueError:
                        if q not in model and q not in str(year):
                            continue
                elif q.startswith("area"):
                    try:
                        op = ">=" if ">=" in q else "<=" if "<=" in q else ">" if ">" in q else "<"
                        threshold = float(q.split(op)[1])
                        if op == ">" and not (area > threshold):
                            continue
                        elif op == ">=" and not (area >= threshold):
                            continue
                        elif op == "<" and not (area < threshold):
                            continue
                        elif op == "<=" and not (area <= threshold):
                            continue
                    except (ValueError, IndexError):
                        pass
                elif q not in model:
                    continue

            results.append({"year": year, "model": model, "area_km2": area,
                          "glacier_px": stats.get("glacier_pixels", 0),
                          "total_px": stats.get("total_pixels", 0)})

    if not results:
        return f"No predictions match '{query}'."

    lines = [f"## Search Results — '{query}'\n"]
    lines.append("| Year | Model | Area (km²) | Glacier Pixels | Coverage |")
    lines.append("|------|-------|------------|----------------|----------|")
    for r in results:
        frac = r["glacier_px"] / max(r["total_px"], 1) * 100
        lines.append(f"| {r['year']} | {r['model']} | {r['area_km2']:.2f} | {r['glacier_px']:,} | {frac:.2f}% |")
    lines.append(f"\n*{len(results)} result(s) found.*")
    return "\n".join(lines)


# ===========================================================================
# MCP RESOURCES — Browse data catalog
# ===========================================================================

@mcp.resource("glacierkz://catalog")
def catalog_resource() -> str:
    """Full data catalog — all years, sources, predictions, models."""
    sources = _discover_sources()
    preds = _discover_predictions()
    all_years = sorted(set(list(sources["sentinel2"].keys()) + list(sources["landsat"].keys())))
    return json.dumps({
        "total_years": len(all_years),
        "years": all_years,
        "sentinel2_years": sorted(sources["sentinel2"].keys()),
        "landsat_years": sorted(sources["landsat"].keys()),
        "prediction_years": sorted(preds.keys()),
        "models": ["ndsi", "rf", "unet", "attention_unet"],
    }, indent=2)


@mcp.resource("glacierkz://pipeline-status")
def pipeline_status_resource() -> str:
    """Machine-readable pipeline status generated from local project files."""
    return json.dumps(_read_json_file(RESULTS_DIR / "pipeline_status.json"), indent=2, ensure_ascii=False)


@mcp.resource("glacierkz://data-quality")
def data_quality_resource() -> str:
    """Machine-readable data quality report for local raster files."""
    return json.dumps(_read_json_file(RESULTS_DIR / "data_quality_report.json"), indent=2, ensure_ascii=False)


@mcp.resource("glacierkz://data-inventory")
def data_inventory_resource() -> str:
    """Machine-readable raster inventory with CRS, shape, dtype, size and hash fields."""
    return json.dumps(_read_json_file(RESULTS_DIR / "data_inventory.json"), indent=2, ensure_ascii=False)


@mcp.resource("glacierkz://decision-readiness")
def decision_readiness_resource() -> str:
    """Machine-readable decision readiness summary and strict trend context."""
    return get_decision_readiness()


@mcp.resource("glacierkz://year/{year}")
def year_resource(year: str) -> str:
    """Detailed info for a specific year's data."""
    y = int(year)
    info = _get_source(y)
    preds = _discover_predictions()
    if info is None:
        return json.dumps({"error": f"Year {y} not found"})
    src_name, path = info
    with rasterio.open(path) as ds:
        meta = {"year": y, "source": src_name, "bands": ds.count,
                "width": ds.width, "height": ds.height, "crs": str(ds.crs),
                "resolution_m": abs(ds.res[0]),
                "file_size_mb": round(path.stat().st_size / (1024*1024), 1)}
    if y in preds:
        meta["predictions"] = preds[y]
    return json.dumps(meta, indent=2)


@mcp.resource("glacierkz://study-area")
def study_area_resource() -> str:
    """Study area metadata: bounding box, glaciers, data sources."""
    return json.dumps({
        "region": "Zailiyskiy Alatau, Kazakhstan",
        "bbox": [76.5, 42.8, 77.5, 43.2],
        "glaciers": ["Туюксу", "Богдановича", "Мутный"],
        "area_km2": 4487,
        "utm_zone": "EPSG:32642",
    }, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if "--sse" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
