"""Transparent spectral QA indicators for annual Sentinel-2 acquisitions."""

from __future__ import annotations

from typing import Any

import numpy as np


def assess_sentinel2_scene(
    bands: np.ndarray,
    *,
    green_index: int = 1,
    red_index: int = 2,
    nir_index: int = 3,
    swir1_index: int = 5,
    known_glacier_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Estimate cloud, shadow, snow, no-data and NDSI from reflectance bands.

    ``bands`` has shape ``(bands, rows, cols)`` and should contain surface
    reflectance. Integer-scaled Sentinel-2 values are automatically divided by
    10,000. These are deterministic spectral QA heuristics, not replacements
    for provider cloud-probability or SCL products.
    """
    array = np.asarray(bands, dtype=np.float64)
    if array.ndim != 3:
        raise ValueError("bands must have shape (bands, rows, cols)")
    required = max(green_index, red_index, nir_index, swir1_index)
    if array.shape[0] <= required:
        raise ValueError(f"at least {required + 1} bands are required")
    finite = np.isfinite(array)
    valid = finite.all(axis=0) & np.any(array != 0, axis=0)
    nodata_fraction = float(1 - valid.mean())
    if not valid.any():
        raise ValueError("scene sample contains no valid pixels")

    valid_values = array[:, valid]
    if np.nanpercentile(valid_values, 99) > 2:
        array = array / 10000.0
    green = array[green_index]
    red = array[red_index]
    nir = array[nir_index]
    swir1 = array[swir1_index]
    blue = array[0]
    denominator = green + swir1
    ndsi = np.divide(green - swir1, denominator, out=np.zeros_like(green), where=np.abs(denominator) > 1e-8)

    visible_brightness = (blue + green + red) / 3
    cloud = valid & (visible_brightness > 0.28) & (swir1 > 0.12) & (ndsi < 0.4)
    shadow = valid & (visible_brightness < 0.07) & (nir < 0.10)
    snow = valid & (ndsi > 0.4) & (green > 0.10)
    if known_glacier_mask is not None:
        glacier = np.asarray(known_glacier_mask, dtype=bool)
        if glacier.shape != valid.shape:
            raise ValueError("known_glacier_mask shape does not match scene")
        off_glacier = valid & ~glacier
        off_glacier_snow_fraction = float(snow[off_glacier].mean()) if off_glacier.any() else 0.0
        off_glacier_available = True
    else:
        off_glacier_snow_fraction = None
        off_glacier_available = False

    valid_count = int(valid.sum())
    return {
        "cloud_fraction": float(cloud.sum() / valid_count),
        "shadow_fraction": float(shadow.sum() / valid_count),
        "snow_fraction": float(snow.sum() / valid_count),
        "off_glacier_snow_fraction": off_glacier_snow_fraction,
        "off_glacier_snow_available": off_glacier_available,
        "nodata_fraction": nodata_fraction,
        "mean_ndsi": float(ndsi[valid].mean()),
        "valid_sample_pixels": valid_count,
        "qa_method": "deterministic_spectral_heuristics_v1",
        "qa_caveat": "Use provider SCL/cloud probability and a glacier mask for release-grade scene acceptance.",
    }


def acquisition_decision(
    quality: dict[str, Any],
    *,
    max_cloud_fraction: float = 0.10,
    max_nodata_fraction: float = 0.10,
    max_off_glacier_snow_fraction: float = 0.20,
) -> tuple[str, list[str]]:
    """Return accept/review/reject with explicit reasons."""
    reasons: list[str] = []
    if float(quality["cloud_fraction"]) > max_cloud_fraction:
        reasons.append("cloud fraction exceeds protocol")
    if float(quality["nodata_fraction"]) > max_nodata_fraction:
        reasons.append("no-data fraction exceeds protocol")
    off_snow = quality.get("off_glacier_snow_fraction")
    if off_snow is not None and float(off_snow) > max_off_glacier_snow_fraction:
        reasons.append("off-glacier seasonal snow exceeds protocol")
    if reasons:
        return "reject", reasons
    if not quality.get("off_glacier_snow_available", False):
        return "review", ["off-glacier snow QA unavailable"]
    return "accept", []
