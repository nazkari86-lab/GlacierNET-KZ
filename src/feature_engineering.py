#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature engineering for ML models.

Extracts texture, spectral, and spatial features from glacier imagery
for downstream machine-learning classifiers (Random Forest, SVM, etc.).

Dual-backend strategy
---------------------
OpenCV (``cv2``) is preferred for morphological, resize, and colour-space
operations.  When ``cv2`` is not available the module falls back to
equivalent ``scipy.ndimage`` routines.

TensorFlow is imported lazily inside functions that actually need it so
that the heavy import cost is paid only when required.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

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


def _to_uint8(image: np.ndarray) -> np.ndarray:
    """Scale a float image to uint8 [0, 255]."""
    if image.dtype == np.uint8:
        return image
    image = image.astype(np.float64)
    vmin, vmax = image.min(), image.max()
    if vmax - vmin < 1e-10:
        return np.zeros_like(image, dtype=np.uint8)
    scaled = (image - vmin) / (vmax - vmin) * 255.0
    return scaled.astype(np.uint8)


def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convert to single-channel grayscale uint8."""
    if image.ndim == 3:
        if image.shape[-1] == 1:
            return _to_uint8(image[:, :, 0])
        # Use first three channels or luminance
        if image.shape[-1] >= 3:
            rgb = image[:, :, :3].astype(np.float64)
            gray = 0.2989 * rgb[:, :, 0] + 0.5870 * rgb[:, :, 1] + 0.1140 * rgb[:, :, 2]
            return _to_uint8(gray)
        return _to_uint8(image[:, :, 0])
    return _to_uint8(image)


def _gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Gaussian blur with cv2/scipy backend."""
    if _HAS_CV2:
        ksize = int(6 * sigma + 1) | 1
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)
    return _sc_gaussian_filter(image, sigma=sigma)


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Registry
    "FEATURE_EXTRACTORS",
    # Texture features
    "extract_texture_features",
    "compute_haralick_features",
    "compute_lbp_features",
    "compute_gabor_features",
    "compute_glcm_features",
    # Spectral features
    "extract_spectral_features",
    # Spatial features
    "extract_spatial_features",
    "compute_edge_features",
    # Combined
    "build_feature_vector",
]

# ---------------------------------------------------------------------------
# Feature extractor registry
# ---------------------------------------------------------------------------


def _extract_texture_wrapper(image: np.ndarray, **kwargs: Any) -> dict[str, float]:
    """Wrapper for texture feature extraction used in the registry."""
    return extract_texture_features(image, **kwargs)


def _extract_spectral_wrapper(image: np.ndarray, **kwargs: Any) -> dict[str, float]:
    """Wrapper for spectral feature extraction used in the registry."""
    if image.ndim == 3:
        bands = {str(c): image[:, :, c] for c in range(image.shape[-1])}
    else:
        bands = {"0": image}
    return extract_spectral_features(bands, **kwargs)


def _extract_spatial_wrapper(image: np.ndarray, **kwargs: Any) -> dict[str, float]:
    """Wrapper for spatial feature extraction used in the registry."""
    if image.ndim == 3:
        mask = np.any(image > 0, axis=-1).astype(np.uint8)
    else:
        mask = (image > 0).astype(np.uint8)
    return extract_spatial_features(mask, **kwargs)


FEATURE_EXTRACTORS: dict[str, Callable[..., dict[str, float]]] = {
    "texture": _extract_texture_wrapper,
    "spectral": _extract_spectral_wrapper,
    "spatial": _extract_spatial_wrapper,
}


# ---------------------------------------------------------------------------
# GLCM (Gray-Level Co-occurrence Matrix) features
# ---------------------------------------------------------------------------


def compute_glcm_features(
    image: np.ndarray,
    distances: list[int] | None = None,
    angles: list[float] | None = None,
    **kwargs: Any,
) -> dict[str, float]:
    """Compute GLCM-based texture features.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` (single-channel).  Multi-band images are
        converted to grayscale internally.
    distances : list of int, optional
        Pixel pair distances (default ``[1]``).
    angles : list of float, optional
        Pixel pair angles in radians (default ``[0, π/4, π/2, 3π/4]``).
    **kwargs
        ``n_levels`` (int) – grey quantisation levels (default 32).

    Returns
    -------
    dict
        Features: ``contrast``, ``dissimilarity``, ``homogeneity``,
        ``energy``, ``correlation``, ``ASM`` (angular second moment).
    """
    gray = _to_gray(image)
    n_levels = kwargs.get("n_levels", 32)

    if distances is None:
        distances = [1]
    if angles is None:
        angles = [0.0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]

    # Quantise grey levels
    quantised = (gray.astype(np.float64) / 256.0 * n_levels).astype(int)
    quantised = np.clip(quantised, 0, n_levels - 1)

    h, w = quantised.shape
    features: dict[str, list[float]] = {
        "contrast": [],
        "dissimilarity": [],
        "homogeneity": [],
        "energy": [],
        "correlation": [],
        "ASM": [],
    }

    for dist in distances:
        for angle in angles:
            # Build GLCM
            cos_a = int(round(np.cos(angle)))
            sin_a = int(round(np.sin(angle)))

            glcm = np.zeros((n_levels, n_levels), dtype=np.float64)
            for i in range(h):
                for j in range(w):
                    ni, nj = i + sin_a, j + cos_a
                    if 0 <= ni < h and 0 <= nj < w:
                        glcm[quantised[i, j], quantised[ni, nj]] += 1

            # Normalise
            total = glcm.sum()
            if total > 0:
                glcm /= total

            # Compute features
            row_idx, col_idx = np.meshgrid(np.arange(n_levels), np.arange(n_levels), indexing="ij")

            contrast = float(np.sum((row_idx - col_idx) ** 2 * glcm))
            dissimilarity = float(np.sum(np.abs(row_idx - col_idx) * glcm))
            homogeneity = float(np.sum(glcm / (1.0 + (row_idx - col_idx) ** 2)))
            energy = float(np.sqrt(np.sum(glcm**2)))
            asm = float(np.sum(glcm**2))

            # Correlation
            mu_row = np.sum(row_idx * glcm)
            mu_col = np.sum(col_idx * glcm)
            sig_row = np.sqrt(np.sum((row_idx - mu_row) ** 2 * glcm))
            sig_col = np.sqrt(np.sum((col_idx - mu_col) ** 2 * glcm))
            if sig_row > 1e-10 and sig_col > 1e-10:
                corr = float(np.sum((row_idx - mu_row) * (col_idx - mu_col) * glcm) / (sig_row * sig_col))
            else:
                corr = 0.0

            features["contrast"].append(contrast)
            features["dissimilarity"].append(dissimilarity)
            features["homogeneity"].append(homogeneity)
            features["energy"].append(energy)
            features["correlation"].append(corr)
            features["ASM"].append(asm)

    # Average across all distance-angle pairs
    result = {}
    for key, values in features.items():
        result[f"glcm_{key}"] = float(np.mean(values))

    return result


# ---------------------------------------------------------------------------
# LBP (Local Binary Pattern) features
# ---------------------------------------------------------------------------


def compute_lbp_features(
    image: np.ndarray,
    radius: int = 1,
    n_points: int = 8,
    **kwargs: Any,
) -> dict[str, float]:
    """Compute Local Binary Pattern histogram features.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` (single-channel).
    radius : int
        LBP radius.
    n_points : int
        Number of sampling points.
    **kwargs
        ``n_bins`` (int) – number of histogram bins (default ``n_points + 2``).

    Returns
    -------
    dict
        ``"lbp_mean"`` – mean LBP value,
        ``"lbp_std"`` – standard deviation of LBP values,
        ``"lbp_hist_{i}"`` – normalised histogram bin values.
    """
    gray = _to_gray(image).astype(np.float64)
    h, w = gray.shape
    n_bins = kwargs.get("n_bins", n_points + 2)

    # Compute LBP
    lbp = np.zeros_like(gray, dtype=np.float64)
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)

    for k, angle in enumerate(angles):
        dy = int(round(radius * np.sin(angle)))
        dx = int(round(radius * np.cos(angle)))

        # Shifted image
        shifted = np.zeros_like(gray)
        # Valid region
        y_src = slice(max(0, -dy), h - max(0, dy))
        x_src = slice(max(0, -dx), w - max(0, dx))
        y_dst = slice(max(0, dy), h - max(0, -dy))
        x_dst = slice(max(0, dx), w - max(0, -dx))
        shifted[y_dst, x_dst] = gray[y_src, x_src]

        bit = (gray >= shifted).astype(np.float64) * (2**k)
        lbp += bit

    # Normalise to [0, 1]
    lbp_max = lbp.max()
    if lbp_max > 0:
        lbp /= lbp_max

    # Histogram
    hist, _ = np.histogram(lbp, bins=n_bins, range=(0, 1), density=True)

    result = {
        "lbp_mean": float(np.mean(lbp)),
        "lbp_std": float(np.std(lbp)),
    }
    for i, val in enumerate(hist):
        result[f"lbp_hist_{i}"] = float(val)

    return result


# ---------------------------------------------------------------------------
# Gabor filter features
# ---------------------------------------------------------------------------


def compute_gabor_features(
    image: np.ndarray,
    frequencies: list[float] | None = None,
    orientations: list[float] | None = None,
    **kwargs: Any,
) -> dict[str, float]:
    """Compute Gabor filter bank features.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` (single-channel).
    frequencies : list of float, optional
        Spatial frequencies (default ``[0.05, 0.1, 0.2, 0.4]``).
    orientations : list of float, optional
        Filter orientations in radians (default 8 evenly spaced).
    **kwargs
        ``sigma`` (float) – Gaussian envelope sigma (default 2.0).

    Returns
    -------
    dict
        ``"gabor_mean_{f}_{o}"`` – mean response,
        ``"gabor_std_{f}_{o}"`` – std of response,
        ``"gabor_energy_{f}_{o}"`` – energy (mean of absolute values).
    """
    gray = _to_gray(image).astype(np.float64)

    if frequencies is None:
        frequencies = [0.05, 0.1, 0.2, 0.4]
    if orientations is None:
        orientations = np.linspace(0, np.pi, 8, endpoint=False).tolist()

    sigma = kwargs.get("sigma", 2.0)
    ksize = int(6 * sigma + 1) | 1

    result: dict[str, float] = {}

    for freq in frequencies:
        for orient in orientations:
            # Build Gabor kernel
            x, y = np.meshgrid(
                np.arange(ksize) - ksize // 2,
                np.arange(ksize) - ksize // 2,
            )

            x_rot = x * np.cos(orient) + y * np.sin(orient)
            y_rot = -x * np.sin(orient) + y * np.cos(orient)

            gabor_real = np.exp(-(x_rot**2 + y_rot**2) / (2 * sigma**2))
            gabor_real *= np.cos(2 * np.pi * freq * x_rot)

            # Apply filter
            if _HAS_CV2:
                response = cv2.filter2D(gray, cv2.CV_64F, gabor_real)
            else:
                from scipy.signal import fftconvolve

                response = fftconvolve(gray, gabor_real, mode="same")

            prefix = f"gabor_{freq:.3f}_{orient:.2f}"
            result[f"{prefix}_mean"] = float(np.mean(response))
            result[f"{prefix}_std"] = float(np.std(response))
            result[f"{prefix}_energy"] = float(np.mean(np.abs(response)))

    return result


# ---------------------------------------------------------------------------
# Haralick features
# ---------------------------------------------------------------------------


def compute_haralick_features(
    image: np.ndarray,
    distances: list[int] | None = None,
    angles: list[float] | None = None,
    **kwargs: Any,
) -> dict[str, float]:
    """Compute Haralick texture features from the GLCM.

    This is a higher-level wrapper around the GLCM that returns the
    standard Haralick feature set.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` (single-channel).
    distances : list of int, optional
        Pixel pair distances (default ``[1]``).
    angles : list of float, optional
        Angles in radians.
    **kwargs
        ``n_levels`` (int) – grey quantisation levels (default 32).

    Returns
    -------
    dict
        Haralick features: ``haralick_contrast``, ``haralick_correlation``,
        ``haralick_energy``, ``haralick_homogeneity``, ``haralick_entropy``.
    """
    glcm_features = compute_glcm_features(image, distances=distances, angles=angles, **kwargs)

    # Entropy from GLCM
    gray = _to_gray(image)
    n_levels = kwargs.get("n_levels", 32)
    quantised = (gray.astype(np.float64) / 256.0 * n_levels).astype(int)
    quantised = np.clip(quantised, 0, n_levels - 1)

    h, w = quantised.shape
    glcm = np.zeros((n_levels, n_levels), dtype=np.float64)
    for i in range(h):
        for j in range(w - 1):
            glcm[quantised[i, j], quantised[i, j + 1]] += 1

    total = glcm.sum()
    if total > 0:
        glcm /= total
        # Shannon entropy
        nonzero = glcm[glcm > 0]
        entropy = -float(np.sum(nonzero * np.log2(nonzero)))
    else:
        entropy = 0.0

    return {
        "haralick_contrast": glcm_features["glcm_contrast"],
        "haralick_correlation": glcm_features["glcm_correlation"],
        "haralick_energy": glcm_features["glcm_energy"],
        "haralick_homogeneity": glcm_features["glcm_homogeneity"],
        "haralick_entropy": entropy,
    }


# ---------------------------------------------------------------------------
# High-level feature extractors
# ---------------------------------------------------------------------------


def extract_texture_features(
    image: np.ndarray,
    **kwargs: Any,
) -> dict[str, float]:
    """Extract a combined set of texture features.

    Aggregates GLCM, LBP, Haralick, and Gabor features into a single
    dictionary.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    **kwargs
        Forwarded to individual feature functions.

    Returns
    -------
    dict
        Merged texture feature dictionary.
    """
    features: dict[str, float] = {}
    features.update(compute_glcm_features(image, **kwargs))
    features.update(compute_lbp_features(image, **kwargs))
    features.update(compute_haralick_features(image, **kwargs))
    features.update(compute_gabor_features(image, **kwargs))
    return features


def extract_spectral_features(
    bands: dict[str, np.ndarray],
    **kwargs: Any,
) -> dict[str, float]:
    """Extract spectral features from multi-band imagery.

    Computes per-band statistics, band ratios, and spectral indices.

    Parameters
    ----------
    bands : dict
        Mapping of band names to 2-D arrays.

    Returns
    -------
    dict
        Spectral features including per-band stats and ratios.
    """
    features: dict[str, float] = {}

    # Per-band statistics
    for name, band in bands.items():
        band_f = band.astype(np.float64)
        valid = band_f[~np.isnan(band_f)]
        if len(valid) == 0:
            continue
        features[f"band_{name}_mean"] = float(np.mean(valid))
        features[f"band_{name}_std"] = float(np.std(valid))
        features[f"band_{name}_min"] = float(np.min(valid))
        features[f"band_{name}_max"] = float(np.max(valid))
        features[f"band_{name}_median"] = float(np.median(valid))
        features[f"band_{name}_skew"] = float(np.mean(((valid - np.mean(valid)) / max(np.std(valid), 1e-10)) ** 3))
        features[f"band_{name}_kurtosis"] = float(
            np.mean(((valid - np.mean(valid)) / max(np.std(valid), 1e-10)) ** 4) - 3.0
        )

    # Band ratios
    band_names = list(bands.keys())
    for i in range(len(band_names)):
        for j in range(i + 1, len(band_names)):
            b1 = bands[band_names[i]].astype(np.float64)
            b2 = bands[band_names[j]].astype(np.float64)
            denom = b1 + b2
            valid = denom != 0
            ratio = np.zeros_like(denom)
            ratio[valid] = (b1[valid] - b2[valid]) / denom[valid]
            features[f"ratio_{band_names[i]}_{band_names[j]}_mean"] = float(
                np.mean(ratio[valid]) if np.any(valid) else 0.0
            )
            features[f"ratio_{band_names[i]}_{band_names[j]}_std"] = float(
                np.std(ratio[valid]) if np.any(valid) else 0.0
            )

    # Common spectral indices if required bands are present
    band_set = set(bands.keys())
    if "red" in band_set and "nir" in band_set:
        red = bands["red"].astype(np.float64)
        nir = bands["nir"].astype(np.float64)
        denom = nir + red
        valid = denom != 0
        ndvi = np.zeros_like(denom)
        ndvi[valid] = (nir[valid] - red[valid]) / denom[valid]
        features["ndvi_mean"] = float(np.mean(ndvi[valid]) if np.any(valid) else 0.0)
        features["ndvi_std"] = float(np.std(ndvi[valid]) if np.any(valid) else 0.0)

    if "green" in band_set and "swir1" in band_set:
        green = bands["green"].astype(np.float64)
        swir1 = bands["swir1"].astype(np.float64)
        denom = green + swir1
        valid = denom != 0
        ndsi = np.zeros_like(denom)
        ndsi[valid] = (green[valid] - swir1[valid]) / denom[valid]
        features["ndsi_mean"] = float(np.mean(ndsi[valid]) if np.any(valid) else 0.0)

    return features


def extract_spatial_features(
    mask: np.ndarray,
    **kwargs: Any,
) -> dict[str, float]:
    """Extract shape and spatial features from a binary mask.

    Parameters
    ----------
    mask : np.ndarray
        Binary mask ``(H, W)``.

    Returns
    -------
    dict
        Spatial features: ``area``, ``perimeter``, ``compactness``,
        ``elongation``, ``solidity``, ``extent``, ``major_axis``,
        ``minor_axis``, ``eccentricity``.
    """
    mask_bin = (mask > 0).astype(np.uint8)

    area = int(np.sum(mask_bin))
    if area == 0:
        return {
            "area": 0,
            "perimeter": 0,
            "compactness": 0,
            "elongation": 0,
            "solidity": 0,
            "extent": 0,
            "major_axis": 0,
            "minor_axis": 0,
            "eccentricity": 0,
        }

    # Perimeter via edge detection
    if _HAS_CV2:
        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        perimeter = sum(cv2.arcLength(c, True) for c in contours)
    else:
        from scipy.ndimage import binary_erosion

        eroded = binary_erosion(mask_bin)
        perimeter = float(np.sum(mask_bin - eroded))

    # Bounding box
    if _HAS_CV2:
        ys, xs = np.where(mask_bin > 0)
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())
    else:
        ys, xs = np.where(mask_bin > 0)
        x_min, x_max = int(xs.min()), int(xs.max())
        y_min, y_max = int(ys.min()), int(ys.max())

    bbox_area = max((x_max - x_min + 1) * (y_max - y_min + 1), 1)
    extent = area / bbox_area

    # Compactness (isoperimetric ratio)
    compactness = (4 * np.pi * area) / max(perimeter**2, 1e-10)

    # Solidity
    if _HAS_CV2 and len(contours) > 0:
        hull_area = sum(cv2.contourArea(cv2.convexHull(c)) for c in contours)
        solidity = area / max(hull_area, 1e-10)
    else:
        solidity = 1.0

    # Elongation via second-order moments
    ys_f = ys.astype(np.float64)
    xs_f = xs.astype(np.float64)
    mu_yy = np.var(ys_f)
    mu_xx = np.var(xs_f)
    mu_xy = np.mean((xs_f - np.mean(xs_f)) * (ys_f - np.mean(ys_f)))

    cov = np.array([[mu_xx, mu_xy], [mu_xy, mu_yy]])
    eigenvalues = np.linalg.eigvalsh(cov)
    eigenvalues = np.maximum(eigenvalues, 0)
    eigenvalues = np.sort(eigenvalues)[::-1]

    major_axis = 2.0 * np.sqrt(eigenvalues[0])
    minor_axis = 2.0 * np.sqrt(max(eigenvalues[1], 0))

    elongation = major_axis / max(minor_axis, 1e-10)
    eccentricity = np.sqrt(max(1.0 - eigenvalues[1] / max(eigenvalues[0], 1e-10), 0.0))

    return {
        "area": area,
        "perimeter": float(perimeter),
        "compactness": float(compactness),
        "elongation": float(elongation),
        "solidity": float(solidity),
        "extent": float(extent),
        "major_axis": float(major_axis),
        "minor_axis": float(minor_axis),
        "eccentricity": float(eccentricity),
    }


def compute_edge_features(
    image: np.ndarray,
    **kwargs: Any,
) -> dict[str, float]:
    """Compute edge-based features.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    **kwargs
        ``canny_low`` (float) – low Canny threshold (default 50),
        ``canny_high`` (float) – high Canny threshold (default 150).

    Returns
    -------
    dict
        ``"edge_density"`` – fraction of edge pixels,
        ``"edge_mean"`` – mean edge magnitude,
        ``"edge_std"`` – std of edge magnitude,
        ``"edge_orientation_mean"`` – mean edge orientation,
        ``"edge_orientation_std"`` – std of edge orientation,
        ``"edge_complexity"`` – ratio of edge pixels to contour pixels.
    """
    gray = _to_gray(image).astype(np.float64)

    # Gradient magnitude and orientation
    if _HAS_CV2:
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    else:
        from scipy.ndimage import sobel

        sobel_x = sobel(gray, axis=1)
        sobel_y = sobel(gray, axis=0)

    magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    orientation = np.arctan2(sobel_y, sobel_x)

    # Binary edge map via Canny
    canny_low = kwargs.get("canny_low", 50)
    canny_high = kwargs.get("canny_high", 150)

    gray_uint8 = _to_uint8(gray)
    if _HAS_CV2:
        edges = cv2.Canny(gray_uint8, canny_low, canny_high)
    else:
        # Simple threshold fallback
        thresh = (canny_low + canny_high) / 2.0
        edges = (magnitude > thresh).astype(np.uint8) * 255

    edge_mask = edges > 0

    edge_density = float(np.mean(edge_mask))
    edge_magnitude = magnitude[edge_mask] if np.any(edge_mask) else np.array([0.0])
    edge_orientation_vals = orientation[edge_mask] if np.any(edge_mask) else np.array([0.0])

    return {
        "edge_density": edge_density,
        "edge_mean": float(np.mean(edge_magnitude)),
        "edge_std": float(np.std(edge_magnitude)),
        "edge_orientation_mean": float(np.mean(edge_orientation_vals)),
        "edge_orientation_std": float(np.std(edge_orientation_vals)),
        "edge_complexity": float(np.sum(edges > 0) / max(np.sum(magnitude > 0), 1)),
    }


# ---------------------------------------------------------------------------
# Combined feature vector
# ---------------------------------------------------------------------------


def build_feature_vector(
    image: np.ndarray,
    mask: np.ndarray | None = None,
    features: list[str] | None = None,
    **kwargs: Any,
) -> np.ndarray:
    """Build a combined feature vector from an image.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    mask : np.ndarray, optional
        Binary mask ``(H, W)``.  When provided, spatial features are
        extracted from it and only masked pixels contribute to
        spectral/texture statistics.
    features : list of str, optional
        Feature groups to include (default ``["texture", "spectral",
        "spatial"]``).
    **kwargs
        Forwarded to individual extractors.

    Returns
    -------
    np.ndarray
        1-D feature vector.
    """
    if features is None:
        features = ["texture", "spectral", "spatial"]

    all_features: dict[str, float] = {}

    if "texture" in features:
        tex = extract_texture_features(image, **kwargs)
        all_features.update(tex)

    if "spectral" in features:
        if image.ndim == 3:
            bands = {str(c): image[:, :, c] for c in range(image.shape[-1])}
        else:
            bands = {"0": image}
        spec = extract_spectral_features(bands, **kwargs)
        all_features.update(spec)

    if "spatial" in features:
        if mask is not None:
            spatial = extract_spatial_features(mask, **kwargs)
            all_features.update(spatial)
        else:
            # Derive mask from image
            if image.ndim == 3:
                derived_mask = np.any(image > 0, axis=-1).astype(np.uint8)
            else:
                derived_mask = (image > 0).astype(np.uint8)
            spatial = extract_spatial_features(derived_mask, **kwargs)
            all_features.update(spatial)

    if "edge" in features:
        edge = compute_edge_features(image, **kwargs)
        all_features.update(edge)

    # Convert to sorted vector for determinism
    keys = sorted(all_features.keys())
    vector = np.array([all_features[k] for k in keys], dtype=np.float64)

    # Replace NaN with 0
    vector = np.nan_to_num(vector, nan=0.0)

    return vector
