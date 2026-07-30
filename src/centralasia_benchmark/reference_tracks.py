"""Independent physical and historical-event reference tracks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .hma_reference import CENTRAL_ASIA_MOUNTAINS

HUGONNET_PERIOD = "2000-01-01_2020-01-01"
COLOCATION_THRESHOLDS_KM = (1, 2, 5, 10)


def build_hugonnet_reference_metrics(
    hdf_path: str | Path,
    *,
    itslive_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarise RGI-13 geodetic mass change without fabricating a glacier crosswalk."""
    import pandas as pd

    path = Path(hdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    frame = pd.read_hdf(path, key="df")
    regional = frame[(frame["reg"] == 13) & (frame["period"] == HUGONNET_PERIOD)].copy()
    regional = regional.replace([np.inf, -np.inf], np.nan).dropna(subset=["area", "dmdtda", "err_dmdtda"])
    regional = regional[regional["area"] > 0]
    if regional.empty:
        raise ValueError("Hugonnet RGI-13 subset is empty")

    weights = regional["area"].to_numpy(dtype=float)
    rates = regional["dmdtda"].to_numpy(dtype=float)
    errors = regional["err_dmdtda"].to_numpy(dtype=float)
    output: dict[str, Any] = {
        "status": "measured_reference",
        "period": HUGONNET_PERIOD,
        "rgi_region": 13,
        "glacier_records": int(len(regional)),
        "total_glacier_area_km2": float(weights.sum() / 1_000_000.0),
        "area_weighted_mass_change_m_we_per_year": float(np.average(rates, weights=weights)),
        "median_mass_change_m_we_per_year": float(np.median(rates)),
        "fraction_glaciers_with_negative_mass_change": float(np.mean(rates < 0)),
        "fraction_glaciers_conservatively_negative": float(np.mean(rates + errors < 0)),
        "median_reported_uncertainty_m_we_per_year": float(np.median(errors)),
        "join_policy": (
            "Regional physical reference only. RGI6 Hugonnet records are not joined to "
            "RGI7 ITS_LIVE samples without an authoritative crosswalk."
        ),
    }
    if itslive_metrics:
        output["itslive_sampled_glaciers"] = itslive_metrics.get("sampled_glaciers")
        output["itslive_valid_velocity_observations"] = itslive_metrics.get("valid_velocity_observations")
        output["itslive_median_velocity_m_per_year"] = itslive_metrics.get(
            "median_of_glacier_median_velocity_m_per_year"
        )
    return output


def build_event_colocation_metrics(
    hma_gpkg_path: str | Path,
    hmaglof_csv_path: str | Path,
) -> dict[str, Any]:
    """Measure event-to-glacier proximity as a descriptive retrospective screen."""
    import geopandas as gpd
    import pandas as pd

    gpkg_path = Path(hma_gpkg_path)
    csv_path = Path(hmaglof_csv_path)
    if not gpkg_path.is_file():
        raise FileNotFoundError(gpkg_path)
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    glaciers = gpd.read_file(gpkg_path, layer="glaicer_2022")
    glaciers = glaciers[glaciers["Mountain"].isin(CENTRAL_ASIA_MOUNTAINS)].copy()
    if glaciers.empty:
        raise ValueError("Central Asia HMA glacier subset is empty")

    raw_events = pd.read_csv(csv_path, encoding="cp1252")
    raw_events = raw_events.dropna(subset=["Lat_lake", "Lon_lake"]).copy()
    events = gpd.GeoDataFrame(
        raw_events,
        geometry=gpd.points_from_xy(raw_events["Lon_lake"], raw_events["Lat_lake"]),
        crs="EPSG:4326",
    )
    min_x, min_y, max_x, max_y = glaciers.total_bounds
    events = events.cx[min_x - 1 : max_x + 1, min_y - 1 : max_y + 1].copy()
    if events.empty:
        raise ValueError("No HMAGLOFDB events intersect the regional screening envelope")

    metric_crs = glaciers.estimate_utm_crs()
    if metric_crs is None:
        raise ValueError("Could not determine a metric CRS for event screening")
    nearest = gpd.sjoin_nearest(
        events.to_crs(metric_crs),
        glaciers.to_crs(metric_crs)[["Mountain", "rgi_id", "geometry"]],
        how="left",
        distance_col="distance_m",
    )
    nearest = nearest.dropna(subset=["distance_m", "rgi_id"])
    if nearest.empty:
        raise ValueError("No event-to-glacier nearest-neighbour matches were produced")

    sensitivity = {}
    for threshold_km in COLOCATION_THRESHOLDS_KM:
        selected = nearest[nearest["distance_m"] <= threshold_km * 1_000]
        sensitivity[str(threshold_km)] = {
            "event_records": int(len(selected)),
            "unique_glaciers": int(selected["rgi_id"].nunique()),
        }

    within_five = nearest[nearest["distance_m"] <= 5_000]
    exact_years = pd.to_numeric(within_five["Year_exact"], errors="coerce").dropna()
    return {
        "status": "measured_reference",
        "hma_glaciers_screened": int(len(glaciers)),
        "hmaglof_events_with_coordinates": int(len(raw_events)),
        "events_in_regional_envelope": int(len(events)),
        "events_within_5km": int(len(within_five)),
        "unique_glaciers_with_event_within_5km": int(within_five["rgi_id"].nunique()),
        "event_year_min_within_5km": int(exact_years.min()) if not exact_years.empty else None,
        "event_year_max_within_5km": int(exact_years.max()) if not exact_years.empty else None,
        "distance_sensitivity_km": sensitivity,
        "distance_crs": metric_crs.to_string(),
        "interpretation": (
            "Descriptive spatial co-location only. Repeated events remain separate records; "
            "proximity is not a causal link, calibrated hazard score or operational warning."
        ),
    }
