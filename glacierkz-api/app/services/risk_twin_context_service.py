"""Spatial evidence context for the research-only Risk Twin.

This service intentionally reports proximity and coverage, not causal links or
event probabilities.  It turns already-hydrated local geodata into auditable
map layers attached to a selected RGI glacier.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.services.glacier_registry_service import CORE_DIR, _load_rgi, _record, get_glacier

WGS84 = "EPSG:4326"
METRIC_CRS = "EPSG:32642"
LAKE_INVENTORY = CORE_DIR / "data/lakes/inventory/hma_gli_2015_2018_ile_alatau.gpkg"
LAKE_TIMESERIES = CORE_DIR / "data/lakes/tien_shan_1990_2023/tien_shan_lakes_ile_alatau_1990_2023.gpkg"
GLOF_EVENTS = CORE_DIR / "data/events/hmaglofdb/hmaglofdb_ile_alatau.gpkg"
CRITICAL_ASSETS = CORE_DIR / "data/impact_assets/osm_critical_assets.geojson"
TERRAIN = CORE_DIR / "data/ancillary/terrain/terrain_features.tif"
SENTINEL1_DIR = CORE_DIR / "data/ancillary/sentinel1"
HYDRORIVERS = CORE_DIR / "data/hydrology/subsets/hydrorivers_study_area.gpkg"
HYDROBASINS = CORE_DIR / "data/hydrology/subsets/hydrobasins_level06_study_area.gpkg"
JRC_SURFACE_WATER = CORE_DIR / "data/water/jrc_gsw_context_100m.tif"
ERA5_MANIFEST = CORE_DIR / "data/climate/manifest.json"
POPULATION_2025 = CORE_DIR / "data/population/kaz_pop_2025_CN_100m_R2025A_v1.tif"
OGGM_STATISTICS = CORE_DIR / "data/external/centralasia_glacierbench/oggm/glacier_statistics_13.csv"
ITSLIVE_SAMPLES = CORE_DIR / "data/external/centralasia_glacierbench/itslive/velocity_samples.parquet"
ITSLIVE_CATALOG = CORE_DIR / "data/external/centralasia_glacierbench/itslive/stac_cubes.json"
LAKE_INVENTORY_YEARS = (1990, 2000, 2010, 2020, 2023)


def _clean(value: Any) -> Any:
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except TypeError:
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


def _feature(row: Any, properties: dict[str, Any]) -> dict[str, Any]:
    from shapely.geometry import mapping

    return {
        "type": "Feature",
        "properties": {key: _clean(value) for key, value in properties.items()},
        "geometry": mapping(row.geometry),
    }


@lru_cache(maxsize=1)
def _sources() -> dict[str, Any]:
    import geopandas as gpd

    if not all(path.is_file() for path in (LAKE_INVENTORY, LAKE_TIMESERIES, GLOF_EVENTS)):
        missing = [
            str(path.relative_to(CORE_DIR))
            for path in (LAKE_INVENTORY, LAKE_TIMESERIES, GLOF_EVENTS)
            if not path.is_file()
        ]
        raise FileNotFoundError(f"Risk Twin context files are missing: {', '.join(missing)}")
    lakes_by_year = {
        year: gpd.read_file(LAKE_TIMESERIES, layer=f"lakes_{year}").to_crs(WGS84)
        for year in (1990, 2000, 2010, 2020, 2023)
    }
    sources = {
        "inventory": gpd.read_file(LAKE_INVENTORY).to_crs(WGS84),
        "lakes_by_year": lakes_by_year,
        "events": gpd.read_file(GLOF_EVENTS).to_crs(WGS84),
    }
    # The full Asia HydroSHEDS source is too large for a map request.  The
    # reproducible builder writes small study-area GeoPackages first.
    if HYDRORIVERS.is_file():
        sources["rivers"] = gpd.read_file(HYDRORIVERS, layer="hydrorivers").to_crs(WGS84)
    if HYDROBASINS.is_file():
        sources["basins"] = gpd.read_file(HYDROBASINS, layer="hydrobasins_level06").to_crs(WGS84)
    return sources


def _within_buffer(frame: Any, geometry: Any, buffer_km: float) -> Any:
    metric_geometry = frame.__class__({"geometry": [geometry]}, crs=WGS84).to_crs(METRIC_CRS).geometry.iloc[0]
    buffered = metric_geometry.buffer(buffer_km * 1000)
    metric_frame = frame.to_crs(METRIC_CRS)
    return metric_frame[metric_frame.intersects(buffered)].to_crs(WGS84)


def _wgs84_buffer_geometry(geometry: Any, buffer_km: float) -> dict[str, Any]:
    """Return a metric straight-line buffer as WGS84 GeoJSON geometry."""
    import geopandas as gpd
    from shapely.geometry import mapping

    metric_geometry = gpd.GeoDataFrame({"geometry": [geometry]}, crs=WGS84).to_crs(METRIC_CRS).geometry.iloc[0]
    buffered = metric_geometry.buffer(buffer_km * 1000)
    wgs84 = gpd.GeoDataFrame({"geometry": [buffered]}, crs=METRIC_CRS).to_crs(WGS84).geometry.iloc[0]
    return mapping(wgs84)


def _impact_assets(glacier_shape: Any, planning_radius_km: float = 10.0, map_feature_limit: int = 25) -> dict[str, Any]:
    """Return only locally cached public assets in a straight-line planning context.

    This deliberately does not claim downstream routing, exposure, population,
    service disruption, or inundation. Those need hydrology and authoritative
    exposure datasets, which are not part of the local release.
    """
    if not CRITICAL_ASSETS.is_file():
        return {
            "available": False,
            "planning_radius_km": planning_radius_km,
            "features": {"type": "FeatureCollection", "features": []},
            "summary": {},
            "reason": "local_osm_critical_asset_extract_not_loaded",
            "interpretation": "No people or infrastructure exposure is inferred until a locally cached, attributed public extract is available.",
        }
    import geopandas as gpd

    assets = gpd.read_file(CRITICAL_ASSETS).to_crs(WGS84)
    nearby = _within_buffer(assets, glacier_shape, planning_radius_km)
    glacier_metric = gpd.GeoDataFrame({"geometry": [glacier_shape]}, crs=WGS84).to_crs(METRIC_CRS).geometry.iloc[0]
    nearby_metric = nearby.to_crs(METRIC_CRS)
    nearby = nearby.assign(_distance_to_rgi_boundary_m=nearby_metric.geometry.distance(glacier_metric)).sort_values(
        "_distance_to_rgi_boundary_m"
    )
    features = []
    counts: dict[str, int] = {}
    for _, row in nearby.iterrows():
        asset_type = str(row.get("asset_type") or "other_public_asset")
        counts[asset_type] = counts.get(asset_type, 0) + 1
    for _, row in nearby.head(map_feature_limit).iterrows():
        asset_type = str(row.get("asset_type") or "other_public_asset")
        features.append(
            _feature(
                row,
                {
                    "asset_type": asset_type,
                    "name": row.get("name"),
                    "source": row.get("source") or "OpenStreetMap",
                    "source_id": row.get("source_id"),
                    "distance_to_rgi_boundary_m": row.get("_distance_to_rgi_boundary_m"),
                    "relation": "straight_line_planning_context_only",
                },
            )
        )
    return {
        "available": True,
        "planning_radius_km": planning_radius_km,
        "features": {"type": "FeatureCollection", "features": features},
        "summary": counts,
        "nearby_asset_count": int(len(nearby)),
        "returned_feature_count": len(features),
        "map_feature_limit": map_feature_limit,
        "source": "OpenStreetMap local extract; see data/impact_assets/manifest.json",
        "interpretation": f"Only the {len(features)} closest public assets inside the {planning_radius_km:g} km straight-line planning context are returned for map inspection. They are not downstream-exposure, affected-population, or disruption estimates.",
    }


def _trace_downstream_route(
    rivers: Any,
    glacier_shape: Any,
    *,
    max_route_km: float = 100.0,
    corridor_width_m: float = 750.0,
    map_feature_limit: int = 25,
) -> dict[str, Any]:
    """Follow the real HydroRIVERS NEXT_DOWN graph from the nearest reach.

    The result is a hydrographic planning route, not a glacier-to-channel
    hydrodynamic connection, travel-time model, flood footprint or warning.
    """
    import geopandas as gpd
    from shapely.geometry import mapping
    from shapely.ops import unary_union

    if rivers is None or rivers.empty:
        return {
            "available": False,
            "status": "hydrorivers_unavailable",
            "features": {"type": "FeatureCollection", "features": []},
            "corridor": None,
            "planning_assets": {"type": "FeatureCollection", "features": []},
        }
    metric_rivers = rivers.to_crs(METRIC_CRS)
    glacier_metric = gpd.GeoDataFrame({"geometry": [glacier_shape]}, crs=WGS84).to_crs(METRIC_CRS).geometry.iloc[0]
    distances = metric_rivers.geometry.distance(glacier_metric)
    start_index = distances.idxmin()
    start_distance_m = float(distances.loc[start_index])
    by_id = {int(row["HYRIV_ID"]): index for index, row in rivers.iterrows()}
    route_indices: list[Any] = []
    seen: set[int] = set()
    current_index = start_index
    total_km = 0.0
    status = "left_local_study_area_subset"
    next_downstream_id: int | None = None
    while current_index is not None:
        row = rivers.loc[current_index]
        reach_id = int(row["HYRIV_ID"])
        if reach_id in seen:
            status = "topology_loop_detected"
            break
        seen.add(reach_id)
        route_indices.append(current_index)
        declared_length = _clean(row.get("LENGTH_KM"))
        total_km += (
            float(declared_length)
            if declared_length is not None
            else float(metric_rivers.loc[current_index].geometry.length / 1000)
        )
        next_downstream_id = int(row.get("NEXT_DOWN") or 0)
        if next_downstream_id == 0:
            status = "reached_hydrorivers_terminal"
            break
        if total_km >= max_route_km:
            status = "distance_cap_reached"
            break
        current_index = by_id.get(next_downstream_id)
        if current_index is None:
            break

    route_metric = metric_rivers.loc[route_indices]
    route_union = unary_union(route_metric.geometry.tolist())
    corridor_metric = route_union.buffer(corridor_width_m)
    corridor_wgs84 = gpd.GeoDataFrame({"geometry": [corridor_metric]}, crs=METRIC_CRS).to_crs(WGS84).geometry.iloc[0]
    route_features = []
    for sequence, index in enumerate(route_indices, start=1):
        row = rivers.loc[index]
        route_features.append(
            _feature(
                row,
                {
                    "source": "HydroSHEDS HydroRIVERS v1.0 NEXT_DOWN topology",
                    "hyriv_id": row.get("HYRIV_ID"),
                    "next_downstream_id": row.get("NEXT_DOWN"),
                    "route_sequence": sequence,
                    "length_km": row.get("LENGTH_KM"),
                    "discharge_cms": row.get("DIS_AV_CMS"),
                    "stream_order": row.get("ORD_STRA"),
                    "relation": "graph_derived_downstream_planning_route",
                },
            )
        )

    planning_assets: list[dict[str, Any]] = []
    asset_counts: dict[str, int] = {}
    total_corridor_assets = 0
    if CRITICAL_ASSETS.is_file():
        assets = gpd.read_file(CRITICAL_ASSETS).to_crs(WGS84)
        metric_assets = assets.to_crs(METRIC_CRS)
        inside = assets.loc[metric_assets.intersects(corridor_metric)].copy()
        total_corridor_assets = int(len(inside))
        for _, row in inside.iterrows():
            asset_type = str(row.get("asset_type") or "other_public_asset")
            asset_counts[asset_type] = asset_counts.get(asset_type, 0) + 1
        for _, row in inside.head(map_feature_limit).iterrows():
            planning_assets.append(
                _feature(
                    row,
                    {
                        "asset_type": row.get("asset_type") or "other_public_asset",
                        "name": row.get("name"),
                        "source": row.get("source") or "OpenStreetMap",
                        "source_id": row.get("source_id"),
                        "relation": "inside_hydrographic_planning_corridor",
                    },
                )
            )

    return {
        "available": True,
        "status": status,
        "start_reach_id": int(rivers.loc[start_index]["HYRIV_ID"]),
        "start_distance_to_rgi_boundary_m": round(start_distance_m, 1),
        "connector_quality": "near" if start_distance_m <= 1000 else "screening_only",
        "route_length_km": round(total_km, 2),
        "route_segment_count": len(route_indices),
        "next_downstream_id_after_subset": next_downstream_id,
        "max_route_km": max_route_km,
        "corridor_width_m": corridor_width_m,
        "features": {"type": "FeatureCollection", "features": route_features},
        "corridor": {
            "type": "Feature",
            "properties": {
                "relation": "planning_buffer_around_hydrorivers_route",
                "width_m": corridor_width_m,
            },
            "geometry": mapping(corridor_wgs84),
        },
        "planning_assets": {"type": "FeatureCollection", "features": planning_assets},
        "planning_asset_summary": asset_counts,
        "planning_asset_count": total_corridor_assets,
        "returned_planning_asset_count": len(planning_assets),
        "interpretation": (
            "The line follows HydroRIVERS NEXT_DOWN topology from the nearest mapped reach. "
            "The shaded corridor only identifies public objects to verify. It is not a "
            "glacier-to-channel connector, inundation footprint, travel-time model, affected-asset count or warning."
        ),
    }


def _raster_summary(path: Path, geometry: dict[str, Any], labels: tuple[str, ...]) -> dict[str, Any]:
    if not path.is_file():
        return {"available": False, "path": str(path.relative_to(CORE_DIR)), "reason": "local_artifact_missing"}
    try:
        import numpy as np
        import rasterio
        from rasterio.mask import mask
        from rasterio.warp import transform_geom

        with rasterio.open(path) as dataset:
            projected = transform_geom(WGS84, dataset.crs, geometry)
            data, _ = mask(dataset, [projected], crop=True, filled=False)
            bands: dict[str, float | None] = {}
            for index, label in enumerate(labels):
                band = data[index]
                values = band.compressed() if hasattr(band, "compressed") else np.asarray(band).ravel()
                finite = values[np.isfinite(values)]
                bands[label] = round(float(np.mean(finite)), 3) if finite.size else None
            return {
                "available": True,
                "path": str(path.relative_to(CORE_DIR)),
                "crs": str(dataset.crs),
                "bands": bands,
                "scope": "mean raster value inside the fixed RGI inventory polygon",
            }
    except Exception as error:  # Raster coverage may not include every selected RGI feature.
        return {"available": False, "path": str(path.relative_to(CORE_DIR)), "reason": type(error).__name__}


def _population_planning_context(glacier_shape: Any, planning_radius_km: float = 30.0) -> dict[str, Any]:
    """Summarise a local population grid without turning it into an impact claim."""
    if not POPULATION_2025.is_file():
        return {
            "available": False,
            "path": str(POPULATION_2025.relative_to(CORE_DIR)),
            "planning_radius_km": planning_radius_km,
            "reason": "local_artifact_missing",
        }
    try:
        import numpy as np
        import rasterio
        from rasterio.mask import mask
        from rasterio.warp import transform_geom

        planning_wgs84 = _wgs84_buffer_geometry(glacier_shape, planning_radius_km)
        with rasterio.open(POPULATION_2025) as dataset:
            projected = transform_geom(WGS84, dataset.crs, planning_wgs84)
            data, _ = mask(dataset, [projected], crop=True, filled=False)
            values = data[0].compressed() if hasattr(data[0], "compressed") else np.asarray(data[0]).ravel()
            values = values[np.isfinite(values) & (values >= 0)]
            return {
                "available": True,
                "path": str(POPULATION_2025.relative_to(CORE_DIR)),
                "reference_year": 2025,
                "planning_radius_km": planning_radius_km,
                "modelled_population_grid_sum": round(float(np.sum(values)), 1) if values.size else 0.0,
                "non_empty_grid_cells": int(np.count_nonzero(values)) if values.size else 0,
                "scope": "Sum of local GHSL modelled population-grid values in a straight-line planning buffer; not affected population, downstream exposure, evacuation demand, or a consequence estimate.",
            }
    except Exception as error:
        return {
            "available": False,
            "path": str(POPULATION_2025.relative_to(CORE_DIR)),
            "planning_radius_km": planning_radius_km,
            "reason": type(error).__name__,
        }


def _climate_catalog_context() -> dict[str, Any]:
    """Expose verified ERA5-Land coverage metadata without fabricating a local series."""
    if not ERA5_MANIFEST.is_file():
        return {
            "available": False,
            "path": str(ERA5_MANIFEST.relative_to(CORE_DIR)),
            "reason": "local_manifest_missing",
        }
    try:
        import json

        manifest = json.loads(ERA5_MANIFEST.read_text(encoding="utf-8"))
        return {
            "available": True,
            "path": str(ERA5_MANIFEST.relative_to(CORE_DIR)),
            "dataset": manifest.get("dataset"),
            "variables": manifest.get("variables", []),
            "years": manifest.get("years", []),
            "bbox_wgs84": manifest.get("bbox_wgs84"),
            "scope": manifest.get("scope"),
            "interpretation": "Local monthly climate coverage is registered, but this endpoint does not yet calculate a glacier-specific anomaly, causal attribution, or forecast.",
        }
    except Exception as error:
        return {"available": False, "path": str(ERA5_MANIFEST.relative_to(CORE_DIR)), "reason": type(error).__name__}


@lru_cache(maxsize=1)
def _benchmark_physical_tables() -> dict[str, Any]:
    """Load compact, read-only benchmark tables used by per-glacier context."""
    import json

    import pandas as pd

    output: dict[str, Any] = {}
    if OGGM_STATISTICS.is_file():
        columns = [
            "rgi_id",
            "inv_volume_km3",
            "vas_volume_km3",
            "dem_mean_elev",
            "main_flowline_length",
            "reference_mb",
            "reference_mb_err",
            "reference_period",
        ]
        output["oggm"] = pd.read_csv(OGGM_STATISTICS, usecols=columns).set_index("rgi_id")
    if ITSLIVE_SAMPLES.is_file():
        output["itslive"] = pd.read_parquet(ITSLIVE_SAMPLES).set_index("rgi_id")
    if ITSLIVE_CATALOG.is_file():
        output["itslive_catalog"] = json.loads(ITSLIVE_CATALOG.read_text(encoding="utf-8")).get("features", [])
    return output


def _benchmark_physical_context(glacier: dict[str, Any]) -> dict[str, Any]:
    """Attach exact RGI7 model context and real ITS_LIVE point observations."""
    tables = _benchmark_physical_tables()
    rgi_id = glacier["rgi_id"]
    longitude = float(glacier["centroid"]["longitude"])
    latitude = float(glacier["centroid"]["latitude"])
    oggm = None
    if "oggm" in tables and rgi_id in tables["oggm"].index:
        row = tables["oggm"].loc[rgi_id]
        oggm = {
            "inventory_based_volume_km3": _clean(row["inv_volume_km3"]),
            "volume_area_scaling_km3": _clean(row["vas_volume_km3"]),
            "dem_mean_elevation_m": _clean(row["dem_mean_elev"]),
            "main_flowline_length_m": _clean(row["main_flowline_length"]),
            "calibration_reference_mass_balance_kg_m2_year": _clean(row["reference_mb"]),
            "calibration_reference_error_kg_m2_year": _clean(row["reference_mb_err"]),
            "calibration_reference_period": _clean(row["reference_period"]),
            "evidence_type": "OGGM physics-model output and calibration context; not direct observation",
        }
    itslive = None
    if "itslive" in tables and rgi_id in tables["itslive"].index:
        row = tables["itslive"].loc[rgi_id]
        itslive = {
            "observations_valid": int(row["observations_valid"]),
            "velocity_m_per_year_median": _clean(row["velocity_m_per_year_median"]),
            "velocity_m_per_year_p90": _clean(row["velocity_m_per_year_p90"]),
            "velocity_m_per_year_max": _clean(row["velocity_m_per_year_max"]),
            "sampling_geometry": "nearest 120 m ITS_LIVE grid point to the RGI7 centroid",
            "evidence_type": "NASA ITS_LIVE observed image-pair velocity point time series",
        }
    coverage = [
        {
            "cube_id": feature["id"],
            "bbox": feature["bbox"],
            "zarr_url": feature["assets"]["zarr"]["href"],
        }
        for feature in tables.get("itslive_catalog", [])
        if feature["bbox"][0] <= longitude <= feature["bbox"][2]
        and feature["bbox"][1] <= latitude <= feature["bbox"][3]
    ]
    allowed = [
        message
        for message in (
            "modelled OGGM context for the exact RGI7 identifier" if oggm else None,
            "observed ITS_LIVE point velocity for the exact RGI7 identifier" if itslive else None,
            "cloud cube coverage discovery" if coverage else None,
        )
        if message is not None
    ]
    return {
        "available": bool(oggm or itslive or coverage),
        "oggm": oggm,
        "itslive_point_sample": itslive,
        "itslive_cloud_coverage": coverage,
        "claim_allowed": allowed,
        "claim_not_allowed": [
            "field-validated glacier volume",
            "whole-glacier velocity from a centroid point",
            "instability, collapse, discharge or event probability",
        ],
    }


def _lake_identifier(row: Any) -> Any:
    """Return the source identifier without guessing an identifier from geometry."""
    return _clean(row.get("GLAKE_ID") or row.get("GLID"))


def _lake_screening_candidates(
    current: Any,
    previous: Any | None,
    glacier_shape: Any,
    historical_count: int,
    inventory_year: int,
    previous_inventory_year: int | None,
) -> list[dict[str, Any]]:
    """Rank real lake observations for follow-up, never for hazard attribution.

    Inventories have different lake identifiers in 2020 and 2023, so matching is
    deliberately geometric and marked as a screening heuristic.  A row answers
    "what should we inspect next?", not "which lake will fail?".
    """
    if current.empty:
        return []
    metric_current = current.to_crs(METRIC_CRS)
    metric_previous = previous.to_crs(METRIC_CRS) if previous is not None else None
    glacier_metric = current.__class__({"geometry": [glacier_shape]}, crs=WGS84).to_crs(METRIC_CRS).geometry.iloc[0]
    candidates: list[dict[str, Any]] = []
    for index, row in metric_current.iterrows():
        centroid = row.geometry.centroid
        distance_to_glacier = float(row.geometry.distance(glacier_metric))
        match_distance = None
        change_percent = None
        previous_area = None
        if metric_previous is not None and not metric_previous.empty:
            distances = metric_previous.geometry.centroid.distance(centroid)
            closest_index = distances.idxmin()
            match_distance = float(distances.loc[closest_index])
            if match_distance <= 300:
                previous_area = float(metric_previous.loc[closest_index, "AREA"] or 0)
                if previous_area > 0:
                    change_percent = (float(row["AREA"] or 0) - previous_area) / previous_area * 100
        flags: list[str] = []
        if previous_area is None:
            flags.append(
                f"no_reliable_{previous_inventory_year}_geometric_match"
                if previous_inventory_year is not None
                else "baseline_inventory_no_earlier_comparison"
            )
        elif abs(change_percent or 0) >= 20:
            flags.append("area_change_at_or_above_20_percent")
        if distance_to_glacier <= 1000:
            flags.append("within_1km_of_rgi_boundary")
        if historical_count:
            flags.append("historical_events_in_same_10km_context")
        area = float(row["AREA"] or 0)
        # Transparent observation-priority components. This is intentionally a
        # data-collection score, not a threat, failure, or probability score.
        change_component = min(abs(change_percent or 0), 40)
        size_component = min(area / 100_000 * 20, 20)
        proximity_component = 20 if distance_to_glacier <= 1000 else 10 if distance_to_glacier <= 5000 else 0
        match_component = 20 if previous_area is None else 0
        priority = round(min(100, 20 + change_component + size_component + proximity_component + match_component), 1)
        original = current.loc[index]
        candidates.append(
            {
                "lake_id": _lake_identifier(original),
                "inventory_year": inventory_year,
                "previous_inventory_year": previous_inventory_year,
                "latitude": round(float(original.get("LAT")), 6),
                "longitude": round(float(original.get("LON")), 6),
                "area_current_m2": round(area, 1),
                "area_previous_m2": round(previous_area, 1) if previous_area is not None else None,
                "area_change_percent": round(change_percent, 1) if change_percent is not None else None,
                "geometric_match_distance_m": round(match_distance, 1) if match_distance is not None else None,
                "distance_to_rgi_boundary_m": round(distance_to_glacier, 1),
                "elevation_m": _clean(original.get("ELEV")),
                "observation_priority_0_100": priority,
                "flags": flags,
                "interpretation": "Real inventory-screening candidate. Priority ranks follow-up value only; it is not a hazard or event probability.",
            }
        )
    return sorted(candidates, key=lambda item: item["observation_priority_0_100"], reverse=True)[:12]


@lru_cache(maxsize=20)
def regional_lake_screening(inventory_year: int = 2023, buffer_km: float = 10.0) -> dict[str, Any]:
    """Automatically screen a selected local lake inventory against its predecessor.

    This is a deterministic regional observation queue.  It intentionally ranks
    follow-up value (change, size, proximity, missing match), not hazard.
    Caching makes page loads fast while keeping the result tied to immutable
    local inventory files; restart or cache-clear is sufficient after an update.
    """
    try:
        sources = _sources()
    except FileNotFoundError as error:
        raise HTTPException(503, str(error)) from error
    available_years = sorted(sources["lakes_by_year"])
    if inventory_year not in available_years:
        raise HTTPException(422, f"Lake inventory year must be one of: {', '.join(map(str, available_years))}")
    previous_year = max((year for year in available_years if year < inventory_year), default=None)
    rgi = _load_rgi().to_crs(METRIC_CRS)
    current = sources["lakes_by_year"][inventory_year].to_crs(METRIC_CRS)
    previous = sources["lakes_by_year"][previous_year].to_crs(METRIC_CRS) if previous_year is not None else None
    events = sources["events"].to_crs(METRIC_CRS)
    rows: list[dict[str, Any]] = []
    rgi_wgs84 = _load_rgi()
    for lake_index, lake in current.iterrows():
        distances = rgi.geometry.distance(lake.geometry)
        rgi_index = distances.idxmin()
        glacier_distance = float(distances.loc[rgi_index])
        if glacier_distance > buffer_km * 1000:
            continue
        glacier_row = rgi.loc[rgi_index]
        centroid = lake.geometry.centroid
        match_distance = None
        previous_area = None
        if previous is not None and not previous.empty:
            previous_distances = previous.geometry.centroid.distance(centroid)
            previous_index = previous_distances.idxmin()
            match_distance = float(previous_distances.loc[previous_index])
            previous_area = float(previous.loc[previous_index, "AREA"] or 0) if match_distance <= 300 else None
        area = float(lake["AREA"] or 0)
        change = ((area - previous_area) / previous_area * 100) if previous_area else None
        historical_count = int((events.geometry.distance(glacier_row.geometry) <= buffer_km * 1000).sum())
        flags: list[str] = []
        if previous_year is None:
            flags.append("baseline_inventory_no_earlier_comparison")
        elif previous_area is None:
            flags.append(f"no_reliable_{previous_year}_geometric_match")
        elif abs(change or 0) >= 20:
            flags.append("area_change_at_or_above_20_percent")
        if glacier_distance <= 1000:
            flags.append("within_1km_of_rgi_boundary")
        if historical_count:
            flags.append("historical_events_in_same_10km_context")
        priority = min(
            100,
            20
            + min(abs(change or 0), 40)
            + min(area / 100_000 * 20, 20)
            + (20 if glacier_distance <= 1000 else 10 if glacier_distance <= 5000 else 0)
            + (20 if previous_year is not None and previous_area is None else 0),
        )
        # Derive public fields from the original WGS84 row; the metric copy is
        # used only for distances.
        original_glacier = rgi_wgs84.loc[rgi_index]
        glacier = _record(original_glacier, include_geometry=False)
        lake_wgs84 = current.loc[[lake_index]].to_crs(WGS84).geometry.iloc[0].centroid
        rows.append(
            {
                "lake_id": _clean(lake.get("GLAKE_ID") or lake.get("GLID")),
                "inventory_year": inventory_year,
                "latitude": round(float(lake_wgs84.y), 6),
                "longitude": round(float(lake_wgs84.x), 6),
                "area_current_m2": round(area, 1),
                "previous_inventory_year": previous_year,
                "area_previous_m2": round(previous_area, 1) if previous_area is not None else None,
                "area_change_percent": round(change, 1) if change is not None else None,
                "geometric_match_distance_m": round(match_distance, 1) if match_distance is not None else None,
                "distance_to_rgi_boundary_m": round(glacier_distance, 1),
                "observation_priority_0_100": round(priority, 1),
                "flags": flags,
                "glacier": {key: glacier[key] for key in ("rgi_id", "name", "name_ru", "centroid", "rgi_area_km2")},
                "historical_event_count_in_glacier_context": historical_count,
                "interpretation": "Automatically found real inventory-screening candidate. Observation priority is not a hazard or event probability.",
            }
        )
    rows.sort(key=lambda item: item["observation_priority_0_100"], reverse=True)
    return {
        "schema": "glaciernet-kz.regional-observation-scan.v1",
        "status": "automatic_local_inventory_screening",
        "inventory_year": inventory_year,
        "previous_inventory_year": previous_year,
        "buffer_km": buffer_km,
        "candidates": rows,
        "summary": {
            "scanned_lakes": int(len(current)),
            "candidates_with_nearby_rgi": len(rows),
            "unmatched_previous": sum(any(flag.startswith("no_reliable_") for flag in row["flags"]) for row in rows),
            "large_change_screening": sum("area_change_at_or_above_20_percent" in row["flags"] for row in rows),
        },
        "limitations": [
            "Matching with the previous available inventory is geometric within 300 m because inventory identifiers differ.",
            "A candidate is a request to inspect source imagery and provenance, not a lake-glacier linkage or hazard claim.",
            "No bathymetry, water level, moraine condition, downstream exposure, event probability, or official warning is inferred.",
        ],
    }


def risk_twin_context(
    rgi_id: str,
    year: int = 2024,
    buffer_km: float = 10.0,
    lake_inventory_year: int = 2023,
) -> dict[str, Any]:
    if year < 2017 or year > 2024:
        raise HTTPException(422, "Sentinel-1 context year must be between 2017 and 2024")
    if buffer_km <= 0 or buffer_km > 30:
        raise HTTPException(422, "buffer_km must be greater than 0 and no more than 30")
    try:
        sources = _sources()
    except FileNotFoundError as error:
        raise HTTPException(503, str(error)) from error
    glacier = get_glacier(rgi_id, include_geometry=True)
    geometry = glacier["geometry"]
    from shapely.geometry import shape

    glacier_shape = shape(geometry)
    inventory = _within_buffer(sources["inventory"], glacier_shape, buffer_km)
    historical = _within_buffer(sources["events"], glacier_shape, buffer_km)
    rivers = _within_buffer(sources["rivers"], glacier_shape, buffer_km) if "rivers" in sources else None
    basins = _within_buffer(sources["basins"], glacier_shape, buffer_km) if "basins" in sources else None
    if lake_inventory_year not in sources["lakes_by_year"]:
        raise HTTPException(422, f"Lake inventory year must be one of: {', '.join(map(str, LAKE_INVENTORY_YEARS))}")
    previous_inventory_year = max(
        (candidate_year for candidate_year in sources["lakes_by_year"] if candidate_year < lake_inventory_year),
        default=None,
    )
    yearly_summary: list[dict[str, Any]] = []
    selected_lakes = None
    previous_lakes = None
    for lake_year, frame in sources["lakes_by_year"].items():
        nearby = _within_buffer(frame, glacier_shape, buffer_km)
        area = float(nearby["AREA"].fillna(0).sum()) if not nearby.empty else 0.0
        yearly_summary.append({"year": lake_year, "lake_count": int(len(nearby)), "total_area_m2": round(area, 1)})
        if lake_year == previous_inventory_year:
            previous_lakes = nearby
        if lake_year == lake_inventory_year:
            selected_lakes = nearby
    inventory_features = [
        _feature(
            row,
            {
                "source": row.source_dataset,
                "period": row.source_period,
                "lake_id": row.Geo_ID,
                "area_m2": row.Area_m2,
                "elevation_m": row.Z,
                "screening_only": bool(row.screening_only),
            },
        )
        for _, row in inventory.iterrows()
    ]
    event_features = [
        _feature(
            row,
            {
                "source": "HMAGLOFDB v1.3.0",
                "event_id": f"HMAGLOFDB-{int(row.GF_ID)}",
                "year": _clean(row.Year_exact) or _clean(row.Year_approx),
                "lake_name": row.Lake_name,
                "glacier_name": row.Glacier_name,
                "lake_type": row.Lake_type,
                "mechanism": row.Mechanism,
                "scientific_reference": row.Ref_scientific,
                "review_status": "database_cited_pending_primary_source_review",
            },
        )
        for _, row in historical.iterrows()
    ]
    river_features = [
        _feature(
            row,
            {
                "source": "HydroSHEDS HydroRIVERS v1.0 local study-area subset",
                "hyriv_id": row.get("HYRIV_ID"),
                "next_downstream_id": row.get("NEXT_DOWN"),
                "length_km": row.get("LENGTH_KM"),
                "discharge_cms": row.get("DIS_AV_CMS"),
                "stream_order": row.get("ORD_STRA"),
                "relation": "hydrographic proximity only; not a routed path",
            },
        )
        for _, row in (rivers.iterrows() if rivers is not None else [])
    ]
    basin_features = [
        _feature(
            row,
            {
                "source": "HydroSHEDS HydroBASINS v1c level 06 local study-area subset",
                "hybas_id": row.get("HYBAS_ID"),
                "next_downstream_id": row.get("NEXT_DOWN"),
                "upstream_area_km2": row.get("UP_AREA"),
                "sub_basin_area_km2": row.get("SUB_AREA"),
                "relation": "basin-context polygon only; not a validated drainage or inundation model",
            },
        )
        for _, row in (basins.iterrows() if basins is not None else [])
    ]
    screening_candidates = (
        _lake_screening_candidates(
            selected_lakes,
            previous_lakes,
            glacier_shape,
            len(event_features),
            lake_inventory_year,
            previous_inventory_year,
        )
        if selected_lakes is not None
        else []
    )
    candidate_by_lake_id = {
        str(candidate["lake_id"]): {**candidate, "screening_rank": rank}
        for rank, candidate in enumerate(screening_candidates, start=1)
        if candidate["lake_id"] is not None
    }
    current_lakes = [
        _feature(
            row,
            {
                "source": "Tien Shan lake inventory 1990-2023",
                "inventory_year": lake_inventory_year,
                "lake_id": _lake_identifier(row),
                "area_m2": row.get("AREA"),
                "elevation_m": row.get("ELEV"),
                "lake_type": row.get("TYPE"),
                "date": row.get("DATE"),
                **candidate_by_lake_id.get(str(_lake_identifier(row)), {}),
            },
        )
        for _, row in (selected_lakes.iterrows() if selected_lakes is not None else [])
    ]
    sentinel = _raster_summary(SENTINEL1_DIR / f"sentinel1_{year}.tif", geometry, ("VV_x100", "VH_x100"))
    terrain = _raster_summary(TERRAIN, geometry, ("elevation_m", "slope_degrees", "aspect_degrees"))
    jrc_surface_water = _raster_summary(
        JRC_SURFACE_WATER,
        _wgs84_buffer_geometry(glacier_shape, buffer_km),
        ("occurrence_percent", "seasonality_months", "recurrence_percent"),
    )
    if jrc_surface_water.get("available"):
        jrc_surface_water["scope"] = (
            f"Mean JRC surface-water raster values inside the selected {buffer_km:g} km straight-line spatial context; not lake bathymetry, flow state, or a risk estimate."
        )
    impact_assets = _impact_assets(glacier_shape)
    downstream_route = _trace_downstream_route(
        sources.get("rivers"),
        glacier_shape,
        max_route_km=100.0,
        corridor_width_m=750.0,
    )
    population_context = _population_planning_context(glacier_shape)
    climate_context = _climate_catalog_context()
    benchmark_context = _benchmark_physical_context(glacier)
    source_catalog = [
        "HMA_GLI v1 (2015-2018 local subset)",
        "Tien Shan glacial lakes and GLOF inventory (1990-2023 local subset)",
        "HMAGLOFDB v1.3.0 local subset",
        "Copernicus DEM-derived terrain features",
        f"Sentinel-1 summer composite {year}",
    ]
    if river_features or basin_features:
        source_catalog.append("HydroSHEDS HydroRIVERS v1.0 and HydroBASINS v1c local study-area subsets")
    if jrc_surface_water["available"]:
        source_catalog.append("JRC Global Surface Water local 100 m context raster")
    if climate_context["available"]:
        source_catalog.append("ERA5-Land monthly climate-context catalog (2000-2025)")
    if population_context["available"]:
        source_catalog.append("GHSL modelled population-grid planning context (2025)")
    if benchmark_context["available"]:
        source_catalog.append("CentralAsia-GlacierBench OGGM and NASA ITS_LIVE physical context")
    return {
        "schema": "glaciernet-kz.risk-twin-context.v4",
        "glacier": glacier,
        "query": {
            "year": year,
            "buffer_km": buffer_km,
            "lake_inventory_year": lake_inventory_year,
            "previous_lake_inventory_year": previous_inventory_year,
        },
        "layers": {
            "hma_gli_2015_2018": {"type": "FeatureCollection", "features": inventory_features},
            "tien_shan_lakes": {"type": "FeatureCollection", "features": current_lakes},
            "historical_glof_events": {"type": "FeatureCollection", "features": event_features},
            "hydrorivers": {"type": "FeatureCollection", "features": river_features},
            "hydrobasins_level06": {"type": "FeatureCollection", "features": basin_features},
        },
        "lake_timeseries": yearly_summary,
        "screening_candidates": screening_candidates,
        "impact_assets": impact_assets,
        "downstream_route": downstream_route,
        "terrain": terrain,
        "sentinel1": sentinel,
        "jrc_surface_water": jrc_surface_water,
        "climate_context": climate_context,
        "population_planning_context": population_context,
        "benchmark_physical_context": benchmark_context,
        "interpretation": {
            "allowed": [
                "local spatial context",
                "proximity screening",
                "lake inventory change summary",
                "transparent observation follow-up ranking",
                "terrain, SAR and surface-water coverage summary",
                "hydrographic and basin context",
                "HydroRIVERS NEXT_DOWN graph-derived planning route and corridor inspection",
                "public-asset and population-grid planning context when local attributed extracts are available",
            ],
            "not_allowed": [
                "event probability",
                "causal attribution",
                "official warning",
                "validated lake-to-glacier linkage",
                "bathymetry or dam-state inference",
                "hydrodynamic flow path or glacier-to-channel connector",
                "inundation extent",
                "downstream exposure, affected population, evacuation demand, or disruption estimate",
            ],
            "event_note": "Historical event records remain database-cited and pending primary-source review; their proximity is not a forecast or a causal link.",
        },
        "sources": source_catalog,
    }
