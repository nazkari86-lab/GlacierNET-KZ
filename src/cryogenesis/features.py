"""Feature extraction from declared fixture or physical local sources."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
import xarray as xr
from rasterio.mask import mask
from rasterio.warp import transform_geom

from .schemas import FeatureValue, GlacierFeatureRecord, SourceAsset

MINIMUM_ANCHOR_AREA_KM2 = 0.01


def _feature(
    value: float | int | str,
    unit: str,
    year: int,
    source_id: str,
) -> FeatureValue:
    return FeatureValue(
        value=value,
        unit=unit,
        observed_at=datetime(year, 7, 1, tzinfo=timezone.utc),
        source_id=source_id,
        quality_state="observed",
    )


def load_feature_fixture(
    path: Path,
    project_root: Path,
) -> tuple[list[GlacierFeatureRecord], tuple[SourceAsset, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != (
        "glaciernet-kz.cryogenesis-feature-fixture.v1"
    ):
        raise ValueError("unsupported CryoGenesis feature fixture schema")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    relative_path = path.resolve().relative_to(project_root.resolve()).as_posix()
    source = SourceAsset("fixture", relative_path, digest, len(raw))
    records: list[GlacierFeatureRecord] = []
    for row in payload.get("records", []):
        anchor_year = int(row["anchor_year"])
        outcome_year = int(row["outcome_year"])
        records.append(
            GlacierFeatureRecord(
                rgi_id=str(row["rgi_id"]),
                basin_id=str(row["basin_id"]),
                region_id=str(row["region_id"]),
                split=str(row["split"]),
                anchor_year=anchor_year,
                outcome_year=outcome_year,
                features={
                    "anchor_area_km2": _feature(
                        float(row["area_km2"]),
                        "km2",
                        anchor_year,
                        "fixture",
                    ),
                    "elevation_mean_m": _feature(
                        float(row["elevation_m"]),
                        "m",
                        anchor_year,
                        "fixture",
                    ),
                },
                outcome=_feature(
                    float(row["outcome_fraction"]),
                    "fraction",
                    outcome_year,
                    "fixture",
                ),
            )
        )
    if not records:
        raise ValueError("feature fixture contains no records")
    return records, (source,)


def _mapped_area_km2(
    dataset: rasterio.io.DatasetReader,
    geometry: Any,
    geometry_crs: Any,
) -> float | None:
    projected = transform_geom(
        geometry_crs.to_string(),
        dataset.crs.to_string(),
        geometry.__geo_interface__,
    )
    try:
        pixels, transform = mask(
            dataset,
            [projected],
            crop=True,
            filled=False,
            indexes=1,
        )
    except ValueError:
        return None
    valid = np.asarray(pixels.filled(0)) > 0
    count = int(np.count_nonzero(valid))
    if count == 0:
        return None
    pixel_area_m2 = abs(transform.a * transform.e - transform.b * transform.d)
    return count * pixel_area_m2 / 1_000_000


def _climate_features(
    dataset: xr.Dataset,
    longitude: float,
    latitude: float,
    anchor_year: int,
) -> dict[str, float]:
    point = dataset.sel(
        longitude=longitude,
        latitude=latitude,
        method="nearest",
    )
    cutoff = np.datetime64(f"{anchor_year}-12-31")
    history = point.sel(valid_time=point.valid_time <= cutoff)
    if history.sizes.get("valid_time", 0) == 0:
        raise ValueError("ERA5-Land has no observations before anchor cutoff")
    summer = history.where(
        history.valid_time.dt.month.isin([6, 7, 8]), drop=True
    )
    annual_precipitation = history["tp"].groupby(
        "valid_time.year"
    ).sum().mean()
    return {
        "summer_temperature_c": float(summer["t2m"].mean()) - 273.15,
        "annual_precipitation_m": float(annual_precipitation),
        "snow_depth_m": float(history["sde"].mean()),
    }


def extract_physical_records(
    project_root: Path,
    anchor_year: int,
    outcome_year: int,
) -> tuple[list[GlacierFeatureRecord], list[dict[str, str]]]:
    """Build glacier rows from RGI, ERA5-Land and declared annual masks."""

    root = project_root.resolve()
    inventory = gpd.read_file(root / "data/rgi/rgi_study_area.shp")
    if "rgi_id" not in inventory:
        raise ValueError("RGI inventory is missing rgi_id")
    climate = xr.open_dataset(
        root / "data/climate/era5_land_2000_2025_monthly.nc",
        chunks=None,
    )
    anchor_path = root / "predictions" / str(anchor_year) / "ndsi_mask.tif"
    outcome_path = root / "predictions" / str(outcome_year) / "ndsi_mask.tif"
    records: list[GlacierFeatureRecord] = []
    exclusions: list[dict[str, str]] = []
    with rasterio.open(anchor_path) as anchor_mask, rasterio.open(
        outcome_path
    ) as outcome_mask:
        for _, row in inventory.sort_values("rgi_id").iterrows():
            anchor_area = _mapped_area_km2(
                anchor_mask, row.geometry, inventory.crs
            )
            outcome_area = _mapped_area_km2(
                outcome_mask, row.geometry, inventory.crs
            )
            # At 10 m resolution this requires at least 100 positive anchor
            # pixels. Smaller supports are dominated by pixel quantisation and
            # are excluded using pre-outcome information only.
            rgi_id = str(row["rgi_id"])
            if anchor_area is None:
                exclusions.append(
                    {
                        "rgi_id": rgi_id,
                        "reason": "anchor_observation_unavailable",
                    }
                )
                continue
            if anchor_area < MINIMUM_ANCHOR_AREA_KM2:
                exclusions.append(
                    {
                        "rgi_id": rgi_id,
                        "reason": "anchor_support_below_0.01_km2",
                    }
                )
                continue
            if outcome_area is None:
                exclusions.append(
                    {
                        "rgi_id": rgi_id,
                        "reason": "outcome_observation_unavailable",
                    }
                )
                continue
            climate_values = _climate_features(
                climate,
                float(row["cenlon"]),
                float(row["cenlat"]),
                anchor_year,
            )
            aspect_radians = np.deg2rad(float(row["aspect_deg"]))
            feature_values = {
                "anchor_area_km2": _feature(
                    anchor_area, "km2", anchor_year, "annual_mask"
                ),
                "elevation_min_m": _feature(
                    float(row["zmin_m"]), "m", anchor_year, "rgi_copdem"
                ),
                "elevation_mean_m": _feature(
                    float(row["zmean_m"]), "m", anchor_year, "rgi_copdem"
                ),
                "elevation_max_m": _feature(
                    float(row["zmax_m"]), "m", anchor_year, "rgi_copdem"
                ),
                "elevation_range_m": _feature(
                    float(row["zmax_m"] - row["zmin_m"]),
                    "m",
                    anchor_year,
                    "derived_pre_outcome",
                ),
                "slope_deg": _feature(
                    float(row["slope_deg"]),
                    "degree",
                    anchor_year,
                    "rgi_copdem",
                ),
                "aspect_sin": _feature(
                    float(np.sin(aspect_radians)),
                    "unitless",
                    anchor_year,
                    "derived_pre_outcome",
                ),
                "aspect_cos": _feature(
                    float(np.cos(aspect_radians)),
                    "unitless",
                    anchor_year,
                    "derived_pre_outcome",
                ),
                **{
                    name: _feature(
                        value,
                        (
                            "degree_celsius"
                            if name == "summer_temperature_c"
                            else "m"
                        ),
                        anchor_year,
                        "era5_land",
                    )
                    for name, value in climate_values.items()
                },
                "valid_observation_count": _feature(
                    2, "count", anchor_year, "annual_mask_provenance"
                ),
                "label_tier": _feature(
                    "automated_physical_mask",
                    "category",
                    anchor_year,
                    "annual_mask_provenance",
                ),
                "sensor_family": _feature(
                    "sentinel2",
                    "category",
                    anchor_year,
                    "annual_mask_provenance",
                ),
            }
            records.append(
                GlacierFeatureRecord(
                    rgi_id=rgi_id,
                    basin_id=str(row["o2region"]),
                    region_id=str(row["o1region"]),
                    split="development",
                    anchor_year=anchor_year,
                    outcome_year=outcome_year,
                    features=feature_values,
                    outcome=_feature(
                        (outcome_area - anchor_area) / anchor_area,
                        "fraction",
                        outcome_year,
                        "annual_mask",
                    ),
                )
            )
    climate.close()
    return records, exclusions
