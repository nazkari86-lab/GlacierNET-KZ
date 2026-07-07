#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spectral indices and band math module for GlacierNET-KZ.

Provides standardized implementations of glacier remote sensing indices,
band ratio calculations, and utility functions for multi-spectral analysis
of glacier surfaces from Sentinel-2, Landsat, and other optical sensors.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    # Registry / metadata
    "SPECTRAL_INDICES",
    "list_indices",
    "get_index_info",
    "compute_index",
    # Individual index functions
    "compute_ndsi",
    "compute_ndvi",
    "compute_ndwi",
    "compute_mndwi",
    "compute_bsi",
    "compute_sbi",
    "compute_ndsi_snow_cover",
    "compute_glacier_mask",
    "compute_cloud_mask",
    "compute_evi",
    "compute_ndmi",
    # Band math utilities
    "apply_cloud_mask",
    "stack_bands",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_divide(
    numerator: np.ndarray,
    denominator: np.ndarray,
    nodata: float = -9999.0,
) -> np.ndarray:
    """Element-wise division that returns *nodata* where the denominator is zero."""
    out = np.full_like(numerator, nodata, dtype=np.float64)
    valid = denominator != 0
    out[valid] = numerator[valid] / denominator[valid]
    return out


def _clip_index(arr: np.ndarray, vmin: float = -1.0, vmax: float = 1.0) -> np.ndarray:
    """Clip an index array to its nominal valid range."""
    return np.clip(arr, vmin, vmax)


def _ensure_float(band: np.ndarray) -> np.ndarray:
    """Cast a band to float64 for computation."""
    return band.astype(np.float64)


# ---------------------------------------------------------------------------
# Spectral index registry
# ---------------------------------------------------------------------------
# Each entry stores:
#   name        – short display name
#   description – formula description
#   bands       – list of required band keys
#   valid_range – (min, max) tuple of theoretically valid output values
#   default_params – dict of keyword defaults passed to the compute function

SPECTRAL_INDICES: dict[str, dict] = {
    "ndsi": {
        "name": "Normalized Difference Snow Index",
        "description": "(Green - SWIR1) / (Green + SWIR1)",
        "bands": ["green", "swir1"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "ndvi": {
        "name": "Normalized Difference Vegetation Index",
        "description": "(NIR - Red) / (NIR + Red)",
        "bands": ["nir", "red"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "ndwi": {
        "name": "Normalized Difference Water Index",
        "description": "(Green - NIR) / (Green + NIR)",
        "bands": ["green", "nir"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "mndwi": {
        "name": "Modified Normalized Difference Water Index",
        "description": "(Green - SWIR2) / (Green + SWIR2)",
        "bands": ["green", "swir2"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "bsi": {
        "name": "Bare Soil Index",
        "description": "((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))",
        "bands": ["swir1", "red", "nir", "blue"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "sbi": {
        "name": "Snow/ice Brightness Index",
        "description": "Mean of Green and NIR reflectance",
        "bands": ["green", "nir"],
        "valid_range": (0.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "ndsi_snow_cover": {
        "name": "NDSI Snow Cover Fraction",
        "description": "Fraction of pixels with NDSI > threshold within a kernel",
        "bands": ["green", "swir1"],
        "valid_range": (0.0, 1.0),
        "default_params": {"nodata": -9999.0, "threshold": 0.4},
    },
    "glacier_mask": {
        "name": "Glacier Binary Mask",
        "description": "NDSI > ndsi_thresh AND NDVI < ndvi_thresh",
        "bands": ["green", "swir1", "nir", "red"],
        "valid_range": (0, 1),
        "default_params": {"nodata": -9999.0, "ndsi_thresh": 0.4, "ndvi_thresh": 0.1},
    },
    "cloud_mask": {
        "name": "Cloud Binary Mask",
        "description": "Simple brightness and NDSI threshold cloud detection",
        "bands": ["blue", "green", "red", "nir", "swir1", "swir2"],
        "valid_range": (0, 1),
        "default_params": {
            "nodata": -9999.0,
            "bright_thresh": 0.3,
            "ndsi_thresh": 0.1,
            "nir_thresh": 0.2,
        },
    },
    "evi": {
        "name": "Enhanced Vegetation Index",
        "description": "2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
        "bands": ["nir", "red", "blue"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0, "gain": 2.5, "c1": 6.0, "c2": 7.5, "offset": 1.0},
    },
    "ndmi": {
        "name": "Normalized Difference Moisture Index",
        "description": "(NIR - SWIR1) / (NIR + SWIR1)",
        "bands": ["nir", "swir1"],
        "valid_range": (-1.0, 1.0),
        "default_params": {"nodata": -9999.0},
    },
    "swir_ratio": {
        "name": "SWIR Ratio",
        "description": "SWIR1 / SWIR2",
        "bands": ["swir1", "swir2"],
        "valid_range": (0.0, np.inf),
        "default_params": {"nodata": -9999.0},
    },
    "nir_red_ratio": {
        "name": "NIR/Red Band Ratio",
        "description": "NIR / Red",
        "bands": ["nir", "red"],
        "valid_range": (0.0, np.inf),
        "default_params": {"nodata": -9999.0},
    },
    "green_swir1_ratio": {
        "name": "Green/SWIR1 Band Ratio",
        "description": "Green / SWIR1",
        "bands": ["green", "swir1"],
        "valid_range": (0.0, np.inf),
        "default_params": {"nodata": -9999.0},
    },
    "blue_green_ratio": {
        "name": "Blue/Green Band Ratio",
        "description": "Blue / Green",
        "bands": ["blue", "green"],
        "valid_range": (0.0, np.inf),
        "default_params": {"nodata": -9999.0},
    },
}


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def list_indices() -> list[str]:
    """Return sorted list of all available index names.

    Returns
    -------
    list[str]
        Names registered in :data:`SPECTRAL_INDICES`.
    """
    return sorted(SPECTRAL_INDICES.keys())


def get_index_info(name: str) -> dict:
    """Return metadata dict for a given index.

    Parameters
    ----------
    name : str
        Index key (e.g. ``"ndsi"``).

    Returns
    -------
    dict
        Copy of the registry entry with keys ``name``, ``description``,
        ``bands``, ``valid_range``, ``default_params``.

    Raises
    ------
    KeyError
        If *name* is not found in the registry.
    """
    if name not in SPECTRAL_INDICES:
        raise KeyError(f"Unknown index '{name}'. Available: {', '.join(list_indices())}")
    return dict(SPECTRAL_INDICES[name])


# ---------------------------------------------------------------------------
# Individual index functions
# ---------------------------------------------------------------------------


def compute_ndsi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Normalized Difference Snow Index.

    Formula: ``(Green - SWIR1) / (Green + SWIR1)``

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"swir1"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        NDSI values clipped to [-1, 1].
    """
    green = _ensure_float(bands["green"])
    swir1 = _ensure_float(bands["swir1"])
    result = _safe_divide(green - swir1, green + swir1, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_ndvi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Normalized Difference Vegetation Index.

    Formula: ``(NIR - Red) / (NIR + Red)``

    Parameters
    ----------
    bands : dict
        Must contain ``"nir"`` and ``"red"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        NDVI values clipped to [-1, 1].
    """
    nir = _ensure_float(bands["nir"])
    red = _ensure_float(bands["red"])
    result = _safe_divide(nir - red, nir + red, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_ndwi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Normalized Difference Water Index (McFeeters).

    Formula: ``(Green - NIR) / (Green + NIR)``

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"nir"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        NDWI values clipped to [-1, 1].
    """
    green = _ensure_float(bands["green"])
    nir = _ensure_float(bands["nir"])
    result = _safe_divide(green - nir, green + nir, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_mndwi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Modified Normalized Difference Water Index.

    Formula: ``(Green - SWIR2) / (Green + SWIR2)``

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"swir2"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        MNDWI values clipped to [-1, 1].
    """
    green = _ensure_float(bands["green"])
    swir2 = _ensure_float(bands["swir2"])
    result = _safe_divide(green - swir2, green + swir2, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_bsi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Bare Soil Index.

    Formula: ``((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))``

    Parameters
    ----------
    bands : dict
        Must contain ``"swir1"``, ``"red"``, ``"nir"``, ``"blue"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        BSI values clipped to [-1, 1].
    """
    swir1 = _ensure_float(bands["swir1"])
    red = _ensure_float(bands["red"])
    nir = _ensure_float(bands["nir"])
    blue = _ensure_float(bands["blue"])
    numerator = (swir1 + red) - (nir + blue)
    denominator = (swir1 + red) + (nir + blue)
    result = _safe_divide(numerator, denominator, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_sbi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Snow/ice Brightness Index.

    Formula: ``(Green + NIR) / 2``

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"nir"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        SBI values clipped to [0, 1].
    """
    green = _ensure_float(bands["green"])
    nir = _ensure_float(bands["nir"])
    result = (green + nir) / 2.0
    # Replace nodata locations
    mask = (bands["green"] == nodata) | (bands["nir"] == nodata)
    result[mask] = nodata
    return _clip_index(result, 0.0, 1.0)


def compute_ndsi_snow_cover(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    threshold: float = 0.4,
    **kwargs,
) -> np.ndarray:
    """Compute a binary snow-cover mask from NDSI.

    Pixels with NDSI > *threshold* are classified as snow (1), others as
    no-snow (0).

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"swir1"``.
    nodata : float
        Value used for invalid / masked pixels.
    threshold : float
        NDSI threshold for snow classification (default 0.4).

    Returns
    -------
    np.ndarray
        Binary uint8 array (0/1) with nodata where input was nodata.
    """
    ndsi = compute_ndsi(bands, nodata=nodata)
    out = np.zeros_like(ndsi, dtype=np.uint8)
    valid = ndsi != nodata
    out[valid & (ndsi > threshold)] = 1
    out[~valid] = 0
    return out


def compute_glacier_mask(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    ndsi_thresh: float = 0.4,
    ndvi_thresh: float = 0.1,
    **kwargs,
) -> np.ndarray:
    """Compute a binary glacier mask combining NDSI and NDVI thresholds.

    A pixel is classified as glacier when NDSI > *ndsi_thresh* **and**
    NDVI < *ndvi_thresh*.

    Parameters
    ----------
    bands : dict
        Must contain ``"green"``, ``"swir1"``, ``"nir"``, ``"red"``.
    nodata : float
        Value used for invalid / masked pixels.
    ndsi_thresh : float
        Minimum NDSI for snow/ice (default 0.4).
    ndvi_thresh : float
        Maximum NDVI to exclude vegetation (default 0.1).

    Returns
    -------
    np.ndarray
        Binary uint8 array (1 = glacier, 0 = non-glacier).
    """
    ndsi = compute_ndsi(bands, nodata=nodata)
    ndvi = compute_ndvi(bands, nodata=nodata)
    out = np.zeros_like(ndsi, dtype=np.uint8)
    valid = (ndsi != nodata) & (ndvi != nodata)
    out[valid & (ndsi > ndsi_thresh) & (ndvi < ndvi_thresh)] = 1
    return out


def compute_cloud_mask(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    bright_thresh: float = 0.3,
    ndsi_thresh: float = 0.1,
    nir_thresh: float = 0.2,
    **kwargs,
) -> np.ndarray:
    """Compute a simple cloud mask based on brightness and spectral thresholds.

    Heuristic rules (commonly used for Sentinel-2 / Landsat scenes):

    1. High brightness: mean of Blue, Green, Red > *bright_thresh*
    2. High NDSI: NDSI > *ndsi_thresh* (cirrus / thin ice)
    3. Low NIR: NIR < *nir_thresh* (clouds are reflective in visible,
       absorptive in NIR)

    Parameters
    ----------
    bands : dict
        Must contain ``"blue"``, ``"green"``, ``"red"``, ``"nir"``,
        ``"swir1"``, ``"swir2"``.
    nodata : float
        Value used for invalid / masked pixels.
    bright_thresh : float
        Brightness threshold on visible mean.
    ndsi_thresh : float
        NDSI threshold for cirrus detection.
    nir_thresh : float
        NIR reflectance below which a pixel may be cloud.

    Returns
    -------
    np.ndarray
        Binary uint8 array (1 = cloud, 0 = clear).
    """
    blue = _ensure_float(bands["blue"])
    green = _ensure_float(bands["green"])
    red = _ensure_float(bands["red"])
    nir = _ensure_float(bands["nir"])
    swir1 = _ensure_float(bands["swir1"])

    brightness = (blue + green + red) / 3.0
    ndsi = _safe_divide(green - swir1, green + swir1, nodata)

    out = np.zeros_like(blue, dtype=np.uint8)
    valid = (blue != nodata) & (green != nodata) & (red != nodata)

    cloud_cond = valid & ((brightness > bright_thresh) | (ndsi > ndsi_thresh) | (nir < nir_thresh))
    out[cloud_cond] = 1
    return out


def compute_evi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    gain: float = 2.5,
    c1: float = 6.0,
    c2: float = 7.5,
    offset: float = 1.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Enhanced Vegetation Index.

    Formula: ``gain * (NIR - Red) / (NIR + c1*Red - c2*Blue + offset)``

    Parameters
    ----------
    bands : dict
        Must contain ``"nir"``, ``"red"``, ``"blue"``.
    nodata : float
        Value used for invalid / masked pixels.
    gain : float
        Scaling factor (default 2.5).
    c1 : float
        Coefficient for Red (default 6.0).
    c2 : float
        Coefficient for Blue (default 7.5).
    offset : float
        Additive constant to avoid division by zero (default 1.0).

    Returns
    -------
    np.ndarray
        EVI values clipped to [-1, 1].
    """
    nir = _ensure_float(bands["nir"])
    red = _ensure_float(bands["red"])
    blue = _ensure_float(bands["blue"])
    numerator = gain * (nir - red)
    denominator = nir + c1 * red - c2 * blue + offset
    result = _safe_divide(numerator, denominator, nodata)
    return _clip_index(result, -1.0, 1.0)


def compute_ndmi(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute the Normalized Difference Moisture Index.

    Formula: ``(NIR - SWIR1) / (NIR + SWIR1)``

    Parameters
    ----------
    bands : dict
        Must contain ``"nir"`` and ``"swir1"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        NDMI values clipped to [-1, 1].
    """
    nir = _ensure_float(bands["nir"])
    swir1 = _ensure_float(bands["swir1"])
    result = _safe_divide(nir - swir1, nir + swir1, nodata)
    return _clip_index(result, -1.0, 1.0)


# ---------------------------------------------------------------------------
# Band ratio functions
# ---------------------------------------------------------------------------


def compute_swir_ratio(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute SWIR1 / SWIR2 band ratio.

    Useful for distinguishing snow, ice, and cloud surfaces.

    Parameters
    ----------
    bands : dict
        Must contain ``"swir1"`` and ``"swir2"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        SWIR ratio values (≥ 0).
    """
    swir1 = _ensure_float(bands["swir1"])
    swir2 = _ensure_float(bands["swir2"])
    return _safe_divide(swir1, swir2, nodata)


def compute_nir_red_ratio(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute NIR / Red band ratio.

    Parameters
    ----------
    bands : dict
        Must contain ``"nir"`` and ``"red"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        NIR/Red ratio values (≥ 0).
    """
    nir = _ensure_float(bands["nir"])
    red = _ensure_float(bands["red"])
    return _safe_divide(nir, red, nodata)


def compute_green_swir1_ratio(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute Green / SWIR1 band ratio.

    Parameters
    ----------
    bands : dict
        Must contain ``"green"`` and ``"swir1"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        Green/SWIR1 ratio values (≥ 0).
    """
    green = _ensure_float(bands["green"])
    swir1 = _ensure_float(bands["swir1"])
    return _safe_divide(green, swir1, nodata)


def compute_blue_green_ratio(
    bands: dict[str, np.ndarray],
    nodata: float = -9999.0,
    **kwargs,
) -> np.ndarray:
    """Compute Blue / Green band ratio.

    Parameters
    ----------
    bands : dict
        Must contain ``"blue"`` and ``"green"``.
    nodata : float
        Value used for invalid / masked pixels.

    Returns
    -------
    np.ndarray
        Blue/Green ratio values (≥ 0).
    """
    blue = _ensure_float(bands["blue"])
    green = _ensure_float(bands["green"])
    return _safe_divide(blue, green, nodata)


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

_INDEX_DISPATCH: dict[str, callable] = {
    "ndsi": compute_ndsi,
    "ndvi": compute_ndvi,
    "ndwi": compute_ndwi,
    "mndwi": compute_mndwi,
    "bsi": compute_bsi,
    "sbi": compute_sbi,
    "ndsi_snow_cover": compute_ndsi_snow_cover,
    "glacier_mask": compute_glacier_mask,
    "cloud_mask": compute_cloud_mask,
    "evi": compute_evi,
    "ndmi": compute_ndmi,
    "swir_ratio": compute_swir_ratio,
    "nir_red_ratio": compute_nir_red_ratio,
    "green_swir1_ratio": compute_green_swir1_ratio,
    "blue_green_ratio": compute_blue_green_ratio,
}


def compute_index(index_name: str, bands: dict[str, np.ndarray], **kwargs) -> np.ndarray:
    """Factory: compute any registered spectral index by name.

    Parameters
    ----------
    index_name : str
        Key in :data:`SPECTRAL_INDICES`.
    bands : dict[str, np.ndarray]
        Mapping of band name → 2-D array. Required keys depend on the index.
    **kwargs
        Override default parameters (e.g. ``nodata``, ``threshold``).

    Returns
    -------
    np.ndarray
        2-D array with the computed index values.
    """
    if index_name not in _INDEX_DISPATCH:
        raise KeyError(f"Unknown index '{index_name}'. Available: {', '.join(list_indices())}")
    func = _INDEX_DISPATCH[index_name]
    # Merge defaults from registry with caller overrides
    defaults = SPECTRAL_INDICES[index_name]["default_params"]
    merged = {**defaults, **kwargs}
    return func(bands=bands, **merged)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def apply_cloud_mask(
    image: np.ndarray,
    cloud_mask: np.ndarray,
    fill_value: float = 0.0,
) -> np.ndarray:
    """Apply a binary cloud mask to a multi-band image.

    Parameters
    ----------
    image : np.ndarray
        3-D array of shape ``(bands, height, width)`` or 2-D single-band.
    cloud_mask : np.ndarray
        2-D binary array (1 = cloud, 0 = clear). Must match spatial dims.
    fill_value : float
        Value to fill clouded pixels with (default 0).

    Returns
    -------
    np.ndarray
        Copy of *image* with clouded pixels set to *fill_value*.
    """
    masked = image.copy()
    if masked.ndim == 2:
        masked[cloud_mask == 1] = fill_value
    elif masked.ndim == 3:
        masked[:, cloud_mask == 1] = fill_value
    else:
        raise ValueError(f"Expected 2-D or 3-D array, got {masked.ndim}-D")
    return masked


def stack_bands(bands: dict[str, np.ndarray]) -> np.ndarray:
    """Stack a dictionary of 2-D band arrays into a single 3-D array.

    Bands are stacked in **alphabetical** order of the dictionary keys to
    guarantee reproducibility regardless of insertion order.

    Parameters
    ----------
    bands : dict[str, np.ndarray]
        Mapping of band name → 2-D array. All arrays must share the same
        spatial dimensions.

    Returns
    -------
    np.ndarray
        3-D array of shape ``(n_bands, height, width)``.
    """
    if not bands:
        raise ValueError("bands dict must not be empty")

    sorted_keys = sorted(bands.keys())
    first_shape = bands[sorted_keys[0]].shape
    for key in sorted_keys:
        if bands[key].shape != first_shape:
            raise ValueError(f"Shape mismatch: '{key}' has shape {bands[key].shape}, expected {first_shape}")
    stacked = np.stack([bands[k] for k in sorted_keys], axis=0)
    return stacked
