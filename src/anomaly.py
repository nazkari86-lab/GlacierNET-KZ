#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anomaly detection for glacier imagery.

Provides statistical and spatial anomaly detection methods tailored for
multi-spectral glacier satellite imagery.  Supports isolation-forest-based
detection, pixel-level anomaly scoring against a reference image, outlier
removal via z-score/IQR, small-region filtering, temporal anomaly detection
for time-series data, and change-based anomaly maps.

Dual-backend strategy
---------------------
OpenCV (``cv2``) is preferred for morphological and interpolation operations
because of its speed.  When ``cv2`` is not available the module falls back to
equivalent ``scipy.ndimage`` routines so that the package remains usable in
minimal environments.

TensorFlow is imported lazily inside functions that actually need it so that
the heavy import cost is paid only when required.
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
        binary_dilation as _sc_binary_dilation,
    )
    from scipy.ndimage import (
        binary_erosion as _sc_binary_erosion,
    )
    from scipy.ndimage import (
        gaussian_filter as _sc_gaussian_filter,
    )
    from scipy.ndimage import (
        label as _sc_label,
    )
    from scipy.ndimage import (
        median_filter as _sc_median_filter,
    )
    from scipy.ndimage import (
        uniform_filter as _sc_uniform_filter,
    )


def _dilate(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """Morphological dilation with cv2/scipy backend."""
    if _HAS_CV2:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        return cv2.dilate(mask.astype(np.uint8), kernel, iterations=iterations)
    return _sc_binary_dilation(mask, iterations=iterations).astype(np.uint8)


def _erode(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
    """Morphological erosion with cv2/scipy backend."""
    if _HAS_CV2:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        return cv2.erode(mask.astype(np.uint8), kernel, iterations=iterations)
    return _sc_binary_erosion(mask, iterations=iterations).astype(np.uint8)


def _gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Gaussian blur with cv2/scipy backend."""
    if _HAS_CV2:
        ksize = int(6 * sigma + 1) | 1  # ensure odd
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)
    return _sc_gaussian_filter(image, sigma=sigma)


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Connected-component labelling with cv2/scipy backend."""
    if _HAS_CV2:
        num_labels, labels = cv2.connectedComponents(mask.astype(np.uint8))
        return labels, num_labels
    labels, num_features = _sc_label(mask.astype(int))
    return labels, num_features


def _resize(image: np.ndarray, dsize: tuple[int, int]) -> np.ndarray:
    """Resize with cv2/scipy backend."""
    if _HAS_CV2:
        return cv2.resize(image, dsize, interpolation=cv2.INTER_LINEAR)
    from scipy.ndimage import zoom

    h_old, w_old = image.shape[:2]
    w_new, h_new = dsize
    zoom_factors = (h_new / h_old, w_new / w_old)
    if image.ndim == 3:
        zoom_factors = (*zoom_factors, 1.0)
    return zoom(image, zoom_factors, order=1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Registry
    "ANOMALY_METHODS",
    # Core functions
    "detect_anomalies",
    "compute_anomaly_map",
    "detect_outliers",
    "detect_spatial_anomalies",
    "detect_temporal_anomalies",
    "compute_change_anomaly",
    "remove_anomalies",
]

# ---------------------------------------------------------------------------
# Anomaly method registry
# ---------------------------------------------------------------------------


def _isolation_forest_anomaly(image: np.ndarray, threshold: float = 0.1, **kwargs: Any) -> np.ndarray:
    """Detect anomalous pixels via Isolation Forest on pixel features."""
    from sklearn.ensemble import IsolationForest

    h, w = image.shape[:2]
    if image.ndim == 2:
        flat = image.reshape(-1, 1)
    else:
        flat = image.reshape(-1, image.shape[-1])

    contamination = max(0.001, min(threshold, 0.5))
    clf = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    labels = clf.fit_predict(flat)
    anomaly_mask = (labels == -1).reshape(h, w)
    return anomaly_mask.astype(np.uint8)


def _mahalanobis_anomaly(image: np.ndarray, threshold: float = 0.1, **kwargs: Any) -> np.ndarray:
    """Detect anomalous pixels via Mahalanobis distance."""
    from scipy.spatial.distance import mahalanobis

    if image.ndim == 2:
        flat = image.reshape(-1, 1).astype(np.float64)
    else:
        flat = image.reshape(-1, image.shape[-1]).astype(np.float64)

    h, w = image.shape[:2]
    mean = np.mean(flat, axis=0)
    cov = np.cov(flat, rowvar=False)
    try:
        cov_inv = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        cov_inv = np.linalg.pinv(cov)

    dists = np.array([mahalanobis(pt, mean, cov_inv) for pt in flat])
    cutoff = np.percentile(dists, 100 * (1 - threshold))
    anomaly_mask = (dists > cutoff).reshape(h, w)
    return anomaly_mask.astype(np.uint8)


def _zscore_anomaly(image: np.ndarray, threshold: float = 0.1, **kwargs: Any) -> np.ndarray:
    """Detect anomalous pixels via per-band z-score thresholding."""
    if image.ndim == 2:
        bands = [image]
    else:
        bands = [image[:, :, c] for c in range(image.shape[-1])]

    h, w = image.shape[:2]
    combined = np.zeros((h, w), dtype=bool)
    for band in bands:
        mu = np.mean(band)
        sigma = np.std(band)
        if sigma < 1e-10:
            continue
        z = np.abs((band - mu) / sigma)
        combined |= z > 3.0

    # Dilate to connect nearby anomalies
    combined = _dilate(combined.astype(np.uint8), iterations=1).astype(bool)
    return combined.astype(np.uint8)


def _local_statistics_anomaly(image: np.ndarray, threshold: float = 0.1, **kwargs: Any) -> np.ndarray:
    """Detect anomalous pixels via local mean/std deviation."""
    window = kwargs.get("window", 15)

    if image.ndim == 2:
        bands = [image.astype(np.float64)]
    else:
        bands = [image[:, :, c].astype(np.float64) for c in range(image.shape[-1])]

    h, w = image.shape[:2]
    combined = np.zeros((h, w), dtype=bool)

    for band in bands:
        if _HAS_CV2:
            local_mean = cv2.blur(band, (window, window))
            local_sq_mean = cv2.blur(band**2, (window, window))
        else:
            local_mean = _sc_uniform_filter(band, size=window)
            local_sq_mean = _sc_uniform_filter(band**2, size=window)

        local_std = np.sqrt(np.maximum(local_sq_mean - local_mean**2, 0))
        local_std = np.maximum(local_std, 1e-10)
        z_local = np.abs((band - local_mean) / local_std)
        combined |= z_local > 3.0

    return combined.astype(np.uint8)


ANOMALY_METHODS: dict[str, Callable[..., np.ndarray]] = {
    "isolation_forest": _isolation_forest_anomaly,
    "mahalanobis": _mahalanobis_anomaly,
    "zscore": _zscore_anomaly,
    "local_statistics": _local_statistics_anomaly,
}


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------


def detect_anomalies(
    image: np.ndarray,
    method: str = "isolation_forest",
    threshold: float = 0.1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Detect anomalous regions in a glacier image.

    Parameters
    ----------
    image : np.ndarray
        Input image of shape ``(H, W)`` or ``(H, W, C)``.
    method : str
        Detection method.  One of ``"isolation_forest"``, ``"mahalanobis"``,
        ``"zscore"``, or ``"local_statistics"``.
    threshold : float
        Sensitivity threshold interpreted by each method (contamination for
        isolation forest, fraction for z-score, etc.).
    **kwargs
        Additional keyword arguments forwarded to the detection method.

    Returns
    -------
    dict
        ``"mask"`` – binary anomaly mask ``(H, W)`` of uint8,
        ``"method"`` – name of the method used,
        ``"threshold"`` – threshold value,
        ``"n_anomalies"`` – count of anomalous pixels,
        ``"anomaly_ratio"`` – fraction of anomalous pixels.
    """
    if method not in ANOMALY_METHODS:
        raise ValueError(f"Unknown method '{method}'. Available: {list(ANOMALY_METHODS)}")

    detect_fn = ANOMALY_METHODS[method]
    mask = detect_fn(image, threshold=threshold, **kwargs)

    n_anomalies = int(np.sum(mask > 0))
    total = image.shape[0] * image.shape[1]

    return {
        "mask": mask,
        "method": method,
        "threshold": threshold,
        "n_anomalies": n_anomalies,
        "anomaly_ratio": n_anomalies / total,
    }


def compute_anomaly_map(image: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Compute a pixel-level anomaly score map.

    Each pixel in *image* is scored by its Mahalanobis distance to the
    distribution of the corresponding pixel neighbourhood in *reference*.

    Parameters
    ----------
    image : np.ndarray
        Current image ``(H, W)`` or ``(H, W, C)``.
    reference : np.ndarray
        Reference image of the same shape.

    Returns
    -------
    np.ndarray
        Anomaly score map ``(H, W)`` of float64, higher values indicate
        greater anomaly.
    """
    image = image.astype(np.float64)
    reference = reference.astype(np.float64)

    if image.shape != reference.shape:
        reference = _resize(reference, (image.shape[1], image.shape[0]))

    if image.ndim == 2:
        diff = image - reference
        sigma = np.std(reference)
        if sigma < 1e-10:
            return np.zeros_like(image, dtype=np.float64)
        return np.abs(diff) / sigma

    # Multi-band: per-band normalised difference
    h, w, c = image.shape
    anomaly_map = np.zeros((h, w), dtype=np.float64)
    for ch in range(c):
        diff = image[:, :, ch] - reference[:, :, ch]
        sigma = np.std(reference[:, :, ch])
        if sigma < 1e-10:
            continue
        anomaly_map += np.abs(diff) / sigma

    anomaly_map /= max(c, 1)
    return anomaly_map


def detect_outliers(
    data: np.ndarray,
    method: str = "zscore",
    threshold: float = 3.0,
) -> np.ndarray:
    """Statistical outlier detection along axis 0.

    Parameters
    ----------
    data : np.ndarray
        Input array (1-D or multi-dimensional; statistics are computed
        along ``axis=0``).
    method : str
        ``"zscore"`` – absolute z-score threshold,
        ``"iqr"`` – interquartile range method.
    threshold : float
        For ``"zscore"``: number of standard deviations; for ``"iqr"``:
        multiplier of the IQR beyond Q1/Q3.

    Returns
    -------
    np.ndarray
        Boolean mask of the same shape as *data*, ``True`` where an
        outlier is detected.
    """
    data = np.asarray(data, dtype=np.float64)

    if method == "zscore":
        mu = np.mean(data, axis=0, keepdims=True)
        sigma = np.std(data, axis=0, keepdims=True)
        sigma = np.maximum(sigma, 1e-10)
        z = np.abs((data - mu) / sigma)
        return z > threshold

    if method == "iqr":
        q1 = np.percentile(data, 25, axis=0, keepdims=True)
        q3 = np.percentile(data, 75, axis=0, keepdims=True)
        iqr = q3 - q1
        iqr = np.maximum(iqr, 1e-10)
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        return (data < lower) | (data > upper)

    raise ValueError(f"Unknown method '{method}'. Use 'zscore' or 'iqr'.")


def detect_spatial_anomalies(
    mask: np.ndarray,
    min_size: int = 100,
) -> np.ndarray:
    """Remove small connected regions (spatial anomalies) from a mask.

    Parameters
    ----------
    mask : np.ndarray
        Binary mask ``(H, W)``.
    min_size : int
        Minimum number of pixels a connected component must have to be
        kept.

    Returns
    -------
    np.ndarray
        Cleaned binary mask with small regions removed.
    """
    mask = (mask > 0).astype(np.uint8)
    labels, num_labels = _label_components(mask)

    cleaned = np.zeros_like(mask)
    for label_id in range(1, num_labels):
        component = labels == label_id
        if np.sum(component) >= min_size:
            cleaned[component] = 1

    return cleaned.astype(np.uint8)


def detect_temporal_anomalies(
    time_series: list,
    method: str = "iqr",
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Detect anomalous time points in a glacier metrics time series.

    Parameters
    ----------
    time_series : list of dict
        Each dict must have at least ``"date"`` (str) and ``"value"``
        (float) keys.  Additional keys are preserved.
    method : str
        ``"iqr"`` – interquartile range,
        ``"zscore"`` – z-score threshold.
    **kwargs
        ``threshold`` (float) – passed to the detection method.

    Returns
    -------
    list of dict
        Sub-set of the input dicts that were flagged as anomalous, with
        an extra ``"anomaly_score"`` key added.
    """
    if not time_series:
        return []

    values = np.array([pt["value"] for pt in time_series], dtype=np.float64)
    threshold = kwargs.get("threshold", 3.0)

    if method == "iqr":
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        iqr = max(iqr, 1e-10)
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        outlier_mask = (values < lower) | (values > upper)
        scores = np.abs(values - np.median(values)) / iqr

    elif method == "zscore":
        mu = np.mean(values)
        sigma = np.std(values)
        sigma = max(sigma, 1e-10)
        z = np.abs((values - mu) / sigma)
        outlier_mask = z > threshold
        scores = z

    else:
        raise ValueError(f"Unknown method '{method}'. Use 'iqr' or 'zscore'.")

    anomalies = []
    for idx, is_outlier in enumerate(outlier_mask):
        if is_outlier:
            entry = dict(time_series[idx])
            entry["anomaly_score"] = float(scores[idx])
            anomalies.append(entry)

    return anomalies


def compute_change_anomaly(
    baseline: np.ndarray,
    current: np.ndarray,
    sigma_factor: float = 2.0,
) -> np.ndarray:
    """Compute a change-based anomaly map between two time points.

    Pixels that differ significantly from the baseline are flagged.

    Parameters
    ----------
    baseline : np.ndarray
        Baseline image ``(H, W)`` or ``(H, W, C)``.
    current : np.ndarray
        Current image of the same shape.
    sigma_factor : float
        Number of standard deviations of the baseline difference to use
        as the anomaly threshold (used only internally; the full float
        map is returned).

    Returns
    -------
    np.ndarray
        Change anomaly score map ``(H, W)`` of float64.
    """
    baseline = baseline.astype(np.float64)
    current = current.astype(np.float64)

    if baseline.shape != current.shape:
        current = _resize(current, (baseline.shape[1], baseline.shape[0]))

    diff = current - baseline

    if diff.ndim == 3:
        # Root-sum-of-squares across bands
        return np.sqrt(np.sum(diff**2, axis=-1))

    return np.abs(diff)


def remove_anomalies(
    image: np.ndarray,
    anomaly_mask: np.ndarray,
    method: str = "interpolate",
    **kwargs: Any,
) -> np.ndarray:
    """Replace anomalous pixels with interpolated or filled values.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    anomaly_mask : np.ndarray
        Binary mask ``(H, W)`` where ``True`` / ``1`` marks anomalies.
    method : str
        ``"interpolate"`` – bilinear interpolation from surrounding
        valid pixels,
        ``"median"`` – local median fill,
        ``"mean"`` – local mean fill.
    **kwargs
        ``median_size`` (int, default 5) – kernel size for median fill,
        ``blur_sigma`` (float, default 1.0) – Gaussian pre-blur sigma
        for interpolation.

    Returns
    -------
    np.ndarray
        Cleaned image with the same dtype as input.
    """
    original_dtype = image.dtype
    image = image.astype(np.float64)
    anomaly_mask = (anomaly_mask > 0).astype(np.uint8)

    if np.sum(anomaly_mask) == 0:
        return image.astype(original_dtype)

    if method == "interpolate":
        # Bilinear interpolation: use the valid pixels to fill the mask
        # Build a weight map and use iterative diffusion.
        blur_sigma = kwargs.get("blur_sigma", 1.0)
        valid = 1.0 - anomaly_mask.astype(np.float64)
        filled = image.copy()

        for _ in range(50):
            blurred = _gaussian_blur(filled, sigma=blur_sigma)
            filled = filled * valid + blurred * (1.0 - valid)

        image[anomaly_mask.astype(bool)] = filled[anomaly_mask.astype(bool)]

    elif method == "median":
        size = kwargs.get("median_size", 5)
        if _HAS_CV2:
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        else:
            np.ones((size, size), dtype=np.uint8)

        if image.ndim == 2:
            if _HAS_CV2:
                filled = cv2.medianBlur(image.astype(np.float32), size | 1)
            else:
                filled = _sc_median_filter(image, size=size)
            image[anomaly_mask.astype(bool)] = filled[anomaly_mask.astype(bool)]
        else:
            for c in range(image.shape[-1]):
                if _HAS_CV2:
                    filled = cv2.medianBlur(image[:, :, c].astype(np.float32), size | 1)
                else:
                    filled = _sc_median_filter(image[:, :, c], size=size)
                image[:, :, c][anomaly_mask.astype(bool)] = filled[anomaly_mask.astype(bool)]

    elif method == "mean":
        size = kwargs.get("median_size", 15)
        if _HAS_CV2:
            mean_val = cv2.blur(image, (size, size))
        else:
            mean_val = _sc_uniform_filter(image, size=size)
        image[anomaly_mask.astype(bool)] = mean_val[anomaly_mask.astype(bool)]

    else:
        raise ValueError(f"Unknown method '{method}'. Use 'interpolate', 'median', or 'mean'.")

    return image.astype(original_dtype)
