#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transfer learning between Landsat and Sentinel-2 imagery.

Provides band harmonization, histogram matching, pansharpening, spatial
resampling, multi-spectral cloud detection, and NDVI time-series
computation for cross-sensor glacier analysis.

Dual-backend strategy
---------------------
OpenCV (``cv2``) is preferred for histogram matching, resize, and
morphological operations.  When ``cv2`` is not available the module
falls back to equivalent ``scipy.ndimage`` routines.

TensorFlow is imported lazily inside functions that actually need it
so that the heavy import cost is paid only when required.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dual-backend helpers (cv2 preferred, scipy fallback)
# ---------------------------------------------------------------------------

_HAS_CV2 = False
try:
    import cv2  # type: ignore[import-untyped]

    _HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore[assignment]

    from scipy.ndimage import (
        gaussian_filter as _sc_gaussian_filter,
    )
    from scipy.ndimage import (
        zoom as _sc_zoom,
    )


def _resize(image: np.ndarray, dsize: tuple[int, int]) -> np.ndarray:
    """Resize with cv2/scipy backend."""
    if _HAS_CV2:
        return cv2.resize(image, dsize, interpolation=cv2.INTER_LINEAR)
    h_old, w_old = image.shape[:2]
    w_new, h_new = dsize
    zoom_factors = (h_new / h_old, w_new / w_old)
    if image.ndim == 3:
        zoom_factors = (*zoom_factors, 1.0)
    return _sc_zoom(image, zoom_factors, order=1)


def _histogram_match(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Histogram matching with cv2/scipy backend."""
    if _HAS_CV2:
        # cv2 does not have a direct histogram match; use numpy LUT approach
        src_flat = source.flatten().astype(np.float64)
        ref_flat = reference.flatten().astype(np.float64)

        src_sorted = np.sort(src_flat)
        ref_sorted = np.sort(ref_flat)

        # Build CDFs
        src_cdf = np.arange(1, len(src_sorted) + 1, dtype=np.float64) / len(src_sorted)
        ref_cdf = np.arange(1, len(ref_sorted) + 1, dtype=np.float64) / len(ref_sorted)

        # Build LUT via interpolation
        lut = np.interp(src_cdf, ref_cdf, ref_sorted)

        # Apply LUT
        src_indices = np.searchsorted(src_sorted, source.flatten())
        src_indices = np.clip(src_indices, 0, len(lut) - 1)
        matched = lut[src_indices].reshape(source.shape)
        return matched.astype(np.float64)

    src_flat = source.flatten().astype(np.float64)
    ref_flat = reference.flatten().astype(np.float64)

    src_sorted = np.sort(src_flat)
    ref_sorted = np.sort(ref_flat)

    src_cdf = np.arange(1, len(src_sorted) + 1, dtype=np.float64) / len(src_sorted)
    ref_cdf = np.arange(1, len(ref_sorted) + 1, dtype=np.float64) / len(ref_sorted)

    lut = np.interp(src_cdf, ref_cdf, ref_sorted)
    src_indices = np.searchsorted(src_sorted, source.flatten())
    src_indices = np.clip(src_indices, 0, len(lut) - 1)
    matched = lut[src_indices].reshape(source.shape)
    return matched.astype(np.float64)


def _gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Gaussian blur with cv2/scipy backend."""
    if _HAS_CV2:
        ksize = int(6 * sigma + 1) | 1
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)
    return _sc_gaussian_filter(image, sigma=sigma)


# ---------------------------------------------------------------------------
# Sentinel-2 ↔ Landsat harmonization coefficients
# ---------------------------------------------------------------------------
# Roy et al. (2016) "Surface reflectance (MSLCP) Landsat-8 Collection 1"
# and Claverie et al. (2018) for Sentinel-2 harmonization.

HARMONIZATION_COEFFICIENTS: dict[str, dict[str, Any]] = {
    "sentinel2_to_landsat8": {
        "description": (
            "Coefficients to transform Sentinel-2 surface reflectance to Landsat-8-like reflectance (Roy et al. 2016)."
        ),
        "bands": {
            "blue": {"offset": 0.0015, "scale": 1.1071},
            "green": {"offset": 0.0022, "scale": 1.0926},
            "red": {"offset": 0.0013, "scale": 1.0749},
            "nir": {"offset": 0.0011, "scale": 1.0584},
            "swir1": {"offset": -0.0003, "scale": 1.0329},
            "swir2": {"offset": 0.0002, "scale": 1.0408},
        },
    },
    "landsat8_to_sentinel2": {
        "description": (
            "Inverse coefficients to transform Landsat-8 surface reflectance to Sentinel-2-like reflectance."
        ),
        "bands": {
            "blue": {"offset": -0.00136, "scale": 0.9032},
            "green": {"offset": -0.00201, "scale": 0.9152},
            "red": {"offset": -0.00121, "scale": 0.9302},
            "nir": {"offset": -0.00104, "scale": 0.9450},
            "swir1": {"offset": 0.00029, "scale": 0.9681},
            "swir2": {"offset": -0.00019, "scale": 0.9614},
        },
    },
    "sentinel2_to_landsat7": {
        "description": ("Approximate coefficients for Sentinel-2 to Landsat-7 ETM+."),
        "bands": {
            "blue": {"offset": 0.0020, "scale": 1.1200},
            "green": {"offset": 0.0030, "scale": 1.1050},
            "red": {"offset": 0.0018, "scale": 1.0880},
            "nir": {"offset": 0.0015, "scale": 1.0650},
            "swir1": {"offset": -0.0004, "scale": 1.0400},
            "swir2": {"offset": 0.0003, "scale": 1.0500},
        },
    },
}


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "HARMONIZATION_COEFFICIENTS",
    # Functions
    "harmonize_bands",
    "compute_band_statistics",
    "normalize_to_reference",
    "apply_pansharpening",
    "resample_bands",
    "detect_clouds_multispectral",
    "compute_ndvi_timeseries",
]


def harmonize_bands(
    source: np.ndarray,
    target_stats: dict,
    **kwargs: Any,
) -> np.ndarray:
    """Apply linear band harmonization from one sensor to another.

    The transformation is: ``target = source * scale + offset``.

    Parameters
    ----------
    source : np.ndarray
        Source image ``(H, W, C)``.
    target_stats : dict
        Per-band harmonization coefficients.  Keys are band names or
        integer indices; values are dicts with ``"offset"`` and
        ``"scale"``.  Alternatively, a key matching one of the presets
        in ``HARMONIZATION_COEFFICIENTS`` can be passed via the
        ``preset`` kwarg, and ``target_stats`` is ignored.
    **kwargs
        ``preset`` (str) – key into ``HARMONIZATION_COEFFICIENTS`` to
        use instead of ``target_stats``.

    Returns
    -------
    np.ndarray
        Harmonized image with the same shape as *source*.
    """
    preset = kwargs.get("preset")
    if preset is not None:
        if preset not in HARMONIZATION_COEFFICIENTS:
            raise ValueError(f"Unknown preset '{preset}'. Available: {list(HARMONIZATION_COEFFICIENTS)}")
        target_stats = HARMONIZATION_COEFFICIENTS[preset]["bands"]

    result = source.astype(np.float64).copy()
    c = source.shape[-1] if source.ndim == 3 else 1

    for band_idx in range(c):
        if band_idx in target_stats:
            coeff = target_stats[band_idx]
        elif str(band_idx) in target_stats:
            coeff = target_stats[str(band_idx)]
        else:
            continue

        offset = coeff.get("offset", 0.0)
        scale = coeff.get("scale", 1.0)
        if source.ndim == 3:
            result[:, :, band_idx] = result[:, :, band_idx] * scale + offset
        else:
            result = result * scale + offset

    return np.clip(result, 0.0, 1.0)


def compute_band_statistics(image: np.ndarray) -> dict[str, Any]:
    """Compute per-band descriptive statistics.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.

    Returns
    -------
    dict
        For single-band images: ``{"mean", "std", "min", "max", "median",
        "nodata_fraction"}``.
        For multi-band images: a dict per band indexed by integer.
    """
    image = image.astype(np.float64)

    if image.ndim == 2:
        valid = image[~np.isnan(image)]
        return {
            "mean": float(np.mean(valid)),
            "std": float(np.std(valid)),
            "min": float(np.min(valid)),
            "max": float(np.max(valid)),
            "median": float(np.median(valid)),
            "nodata_fraction": float(np.sum(np.isnan(image)) / image.size),
        }

    stats = {}
    for c in range(image.shape[-1]):
        band = image[:, :, c]
        valid = band[~np.isnan(band)]
        stats[c] = {
            "mean": float(np.mean(valid)) if len(valid) > 0 else 0.0,
            "std": float(np.std(valid)) if len(valid) > 0 else 0.0,
            "min": float(np.min(valid)) if len(valid) > 0 else 0.0,
            "max": float(np.max(valid)) if len(valid) > 0 else 0.0,
            "median": float(np.median(valid)) if len(valid) > 0 else 0.0,
            "nodata_fraction": float(np.sum(np.isnan(band)) / band.size),
        }

    return stats


def normalize_to_reference(
    image: np.ndarray,
    reference: np.ndarray,
    **kwargs: Any,
) -> np.ndarray:
    """Normalize *image* so its histogram matches *reference*.

    Uses histogram specification (matching) on a per-band basis.

    Parameters
    ----------
    image : np.ndarray
        Source image ``(H, W)`` or ``(H, W, C)``.
    reference : np.ndarray
        Reference image of the same shape (or ``(H, W)`` for single-band).
    **kwargs
        ``n_bins`` (int) – number of histogram bins (default 256).

    Returns
    -------
    np.ndarray
        Histogram-matched image.
    """
    if image.shape != reference.shape:
        reference = _resize(reference, (image.shape[1], image.shape[0]))

    if image.ndim == 2:
        return _histogram_match(image, reference)

    result = np.zeros_like(image, dtype=np.float64)
    for c in range(image.shape[-1]):
        result[:, :, c] = _histogram_match(
            image[:, :, c].astype(np.float64),
            reference[:, :, c].astype(np.float64),
        )

    return result


def apply_pansharpening(
    low_res: np.ndarray,
    high_res: np.ndarray,
    method: str = "brovey",
    **kwargs: Any,
) -> np.ndarray:
    """Fuse a low-resolution multi-band image with a high-resolution panchromatic band.

    Parameters
    ----------
    low_res : np.ndarray
        Low-resolution multi-band image ``(H_lr, W_lr, C)``.
    high_res : np.ndarray
        High-resolution panchromatic image ``(H_hr, W_hr)``.
    method : str
        ``"brovey"`` – Brovey transform,
        ``"ihs"`` – Intensity-Hue-Saturation substitution,
        ``"mean"`` – simple mean fusion.

    Returns
    -------
    np.ndarray
        Pansharpened multi-band image ``(H_hr, W_hr, C)``.
    """
    low_res = low_res.astype(np.float64)
    high_res = high_res.astype(np.float64)

    # Upsample low-res to high-res grid
    h_hr, w_hr = high_res.shape[:2]
    upsampled = _resize(low_res, (w_hr, h_hr))

    upsampled.shape[-1] if upsampled.ndim == 3 else 1

    if method == "brovey":
        # Brovey: band_i * (pan / sum_bands)
        if upsampled.ndim == 2:
            upsampled = upsampled[:, :, np.newaxis]
        band_sum = np.sum(upsampled, axis=-1)
        band_sum = np.maximum(band_sum, 1e-10)
        ratio = high_res / band_sum
        result = upsampled * ratio[:, :, np.newaxis]

    elif method == "ihs":
        # IHS: convert to IHS, replace I with pan, convert back
        if upsampled.ndim == 2 or upsampled.shape[-1] < 3:
            result = upsampled if upsampled.ndim == 3 else upsampled[:, :, np.newaxis]
        else:
            # Simple IHS approximation for arbitrary band count
            intensity = np.mean(upsampled, axis=-1)
            intensity_new = high_res
            gain = np.where(
                np.abs(intensity) > 1e-10,
                intensity_new / intensity,
                1.0,
            )
            result = upsampled * gain[:, :, np.newaxis]

    elif method == "mean":
        result = (upsampled + high_res[:, :, np.newaxis]) / 2.0

    else:
        raise ValueError(f"Unknown method '{method}'. Use 'brovey', 'ihs', or 'mean'.")

    return np.clip(result, 0.0, None)


def resample_bands(
    image: np.ndarray,
    target_resolution: float,
    source_resolution: float = 10.0,
    **kwargs: Any,
) -> np.ndarray:
    """Resample a multi-band image to a target spatial resolution.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    target_resolution : float
        Desired pixel size in the same units as *source_resolution*.
    source_resolution : float
        Original pixel size.
    **kwargs
        ``method`` (str) – ``"linear"`` (default) or ``"nearest"``.

    Returns
    -------
    np.ndarray
        Resampled image.
    """
    method = kwargs.get("method", "linear")

    scale = source_resolution / target_resolution
    new_h = int(round(image.shape[0] * scale))
    new_w = int(round(image.shape[1] * scale))

    if _HAS_CV2:
        interp = cv2.INTER_LINEAR if method == "linear" else cv2.INTER_NEAREST
        return cv2.resize(image, (new_w, new_h), interpolation=interp)

    order = 1 if method == "linear" else 0
    zoom_factors = (new_h / image.shape[0], new_w / image.shape[1])
    if image.ndim == 3:
        zoom_factors = (*zoom_factors, 1.0)
    return _sc_zoom(image, zoom_factors, order=order)


def detect_clouds_multispectral(
    bands: dict[str, np.ndarray],
    **kwargs: Any,
) -> np.ndarray:
    """Detect cloud cover using multi-spectral thresholding.

    Uses a simplified Fmask-like approach combining brightness, NDCI
    (cloud index), and SWIR reflectance.

    Parameters
    ----------
    bands : dict
        Mapping of band names to 2-D arrays.  Expected keys:
        ``"blue"``, ``"green"``, ``"red"``, ``"nir"``, ``"swir1"``,
        ``"swir2"`` (at minimum ``"blue"``, ``"nir"``, ``"swir1"``).
    **kwargs
        ``brightness_threshold`` (float) – minimum brightness (default 0.3),
        ``swir_threshold`` (float) – SWIR reflectance below which cloud
        is likely (default 0.15).

    Returns
    -------
    np.ndarray
        Binary cloud mask ``(H, W)`` of uint8, 1 = cloud.
    """
    brightness_threshold = kwargs.get("brightness_threshold", 0.3)
    swir_threshold = kwargs.get("swir_threshold", 0.15)

    # Determine output shape from available bands
    for key in ("blue", "green", "red", "nir", "swir1"):
        if key in bands:
            h, w = bands[key].shape[:2]
            break
    else:
        raise ValueError("bands dict must contain at least one of 'blue', 'green', 'red', 'nir', or 'swir1'.")

    mask = np.zeros((h, w), dtype=np.uint8)

    blue = bands.get("blue", np.zeros((h, w)))
    green = bands.get("green", np.zeros((h, w)))
    red = bands.get("red", np.zeros((h, w)))
    nir = bands.get("nir", np.zeros((h, w)))
    swir1 = bands.get("swir1", np.ones((h, w)))
    bands.get("swir2", np.ones((h, w)))

    brightness = (blue + green + red + nir) / 4.0

    # Cloud index: high visible, low SWIR
    cloud_score = brightness - swir1

    mask[(brightness > brightness_threshold) & (swir1 < swir_threshold)] = 1
    mask[cloud_score > 0.2] = 1

    # Morphological cleanup
    if _HAS_CV2:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    else:
        from scipy.ndimage import binary_closing, binary_opening

        struct = np.ones((3, 3), dtype=bool)
        mask = binary_opening(mask, structure=struct).astype(np.uint8)
        mask = binary_closing(mask, structure=struct).astype(np.uint8)

    return mask


def compute_ndvi_timeseries(
    images: list[np.ndarray],
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute NDVI values for a list of images over time.

    Parameters
    ----------
    images : list of np.ndarray
        Each element is either a 2-band array ``[nir, red]`` of shape
        ``(2, H, W)`` or ``(H, W, 2)`` with ``nir`` in the last band,
        or a dict with ``"nir"`` and ``"red"`` keys.
    **kwargs
        ``dates`` (list of str) – date labels for each image.

    Returns
    -------
    dict
        ``"ndvi_values"`` – list of per-image mean NDVI,
        ``"ndvi_maps"`` – list of NDVI arrays (or ``None`` if
        ``return_maps=False``),
        ``"dates"`` – date labels,
        ``"mean_ndvi"`` – overall mean,
        ``"std_ndvi"`` – overall standard deviation,
        ``"trend"`` – linear slope (NDVI units per step).
    """
    return_maps = kwargs.get("return_maps", True)
    dates = kwargs.get("dates", [f"t{i}" for i in range(len(images))])

    ndvi_values: list[float] = []
    ndvi_maps: list[np.ndarray | None] = []

    for img in images:
        if isinstance(img, dict):
            nir = img["nir"].astype(np.float64)
            red = img["red"].astype(np.float64)
        elif img.ndim == 3 and img.shape[-1] >= 2:
            nir = img[:, :, -2].astype(np.float64)
            red = img[:, :, -1].astype(np.float64)
        elif img.ndim == 3 and img.shape[0] >= 2:
            nir = img[-2, :, :].astype(np.float64)
            red = img[-1, :, :].astype(np.float64)
        else:
            raise ValueError("Each image must be [nir, red] shaped or a dict with 'nir' and 'red' keys.")

        denominator = nir + red
        denominator = np.maximum(denominator, 1e-10)
        ndvi = (nir - red) / denominator
        ndvi = np.clip(ndvi, -1.0, 1.0)

        ndvi_values.append(float(np.mean(ndvi)))
        ndvi_maps.append(ndvi if return_maps else None)

    ndvi_arr = np.array(ndvi_values, dtype=np.float64)

    # Linear trend
    if len(ndvi_arr) >= 2:
        x = np.arange(len(ndvi_arr), dtype=np.float64)
        slope = float(np.polyfit(x, ndvi_arr, 1)[0])
    else:
        slope = 0.0

    return {
        "ndvi_values": ndvi_values,
        "ndvi_maps": ndvi_maps,
        "dates": dates,
        "mean_ndvi": float(np.mean(ndvi_arr)),
        "std_ndvi": float(np.std(ndvi_arr)),
        "trend": slope,
    }
