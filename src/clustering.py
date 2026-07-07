#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clustering for glacier segmentation analysis.

Provides unsupervised clustering of multi-spectral glacier imagery and
segment-level grouping.  Supports k-means, mini-batch k-means, and
hierarchical clustering with a dual-backend approach (cv2 for image
operations, scipy as fallback).

Dual-backend strategy
---------------------
OpenCV (``cv2``) is preferred for morphological and resize operations.
When ``cv2`` is not available the module falls back to equivalent
``scipy.ndimage`` routines.

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
        label as _sc_label,
    )
    from scipy.ndimage import (
        zoom as _sc_zoom,
    )


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


def _label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """Connected-component labelling with cv2/scipy backend."""
    if _HAS_CV2:
        num_labels, labels = cv2.connectedComponents(mask.astype(np.uint8))
        return labels, num_labels
    labels, num_features = _sc_label(mask.astype(int))
    return labels, num_features


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Registry
    "CLUSTERING_METHODS",
    # Core functions
    "cluster_pixels",
    "cluster_segments",
    "compute_spectral_clusters",
    "segment_by_threshold",
    "compute_cluster_stats",
    "merge_clusters",
    "silhouette_score",
]

# ---------------------------------------------------------------------------
# Clustering method registry
# ---------------------------------------------------------------------------


def _kmeans_cluster(data: np.ndarray, n_clusters: int = 5, **kwargs: Any) -> np.ndarray:
    """K-means clustering."""
    from sklearn.cluster import KMeans

    clf = KMeans(
        n_clusters=n_clusters,
        n_init=10,
        max_iter=300,
        random_state=kwargs.get("random_state", 42),
    )
    labels = clf.fit_predict(data)
    return labels


def _minibatch_kmeans_cluster(data: np.ndarray, n_clusters: int = 5, **kwargs: Any) -> np.ndarray:
    """Mini-batch k-means for large images."""
    from sklearn.cluster import MiniBatchKMeans

    clf = MiniBatchKMeans(
        n_clusters=n_clusters,
        n_init=3,
        max_iter=100,
        batch_size=kwargs.get("batch_size", 1024),
        random_state=kwargs.get("random_state", 42),
    )
    labels = clf.fit_predict(data)
    return labels


CLUSTERING_METHODS: dict[str, Callable[..., np.ndarray]] = {
    "kmeans": _kmeans_cluster,
    "minibatch_kmeans": _minibatch_kmeans_cluster,
}


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------


def cluster_pixels(
    image: np.ndarray,
    n_clusters: int = 5,
    method: str = "kmeans",
    **kwargs: Any,
) -> np.ndarray:
    """Cluster pixels of a multi-spectral image.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` or ``(H, W, C)``.
    n_clusters : int
        Number of clusters.
    method : str
        ``"kmeans"`` or ``"minibatch_kmeans"``.
    **kwargs
        Forwarded to the clustering method (``random_state``, ``batch_size``).

    Returns
    -------
    np.ndarray
        Label map ``(H, W)`` of int32 with values ``0 … n_clusters-1``.
    """
    h, w = image.shape[:2]

    if image.ndim == 2:
        data = image.reshape(-1, 1).astype(np.float64)
    else:
        data = image.reshape(-1, image.shape[-1]).astype(np.float64)

    if method not in CLUSTERING_METHODS:
        raise ValueError(f"Unknown method '{method}'. Available: {list(CLUSTERING_METHODS)}")

    labels = CLUSTERING_METHODS[method](data, n_clusters=n_clusters, **kwargs)
    return labels.reshape(h, w).astype(np.int32)


def cluster_segments(
    masks: list[np.ndarray],
    method: str = "hierarchical",
    **kwargs: Any,
) -> dict[str, Any]:
    """Cluster similar segmentation masks together.

    Each mask is flattened and treated as a feature vector.  Similar
    masks end up in the same cluster.

    Parameters
    ----------
    masks : list of np.ndarray
        Binary masks ``(H, W)`` to cluster.
    method : str
        ``"hierarchical"`` – agglomerative clustering,
        ``"kmeans"`` – k-means on flattened masks.
    **kwargs
        ``n_clusters`` (int) – number of groups (default 2 for
        hierarchical, ``ceil(len(masks)/2)`` for k-means).

    Returns
    -------
    dict
        ``"labels"`` – list of cluster ids per mask,
        ``"n_clusters"`` – number of clusters,
        ``"method"`` – clustering method used,
        ``"cluster_sizes"`` – dict mapping cluster id to count.
    """
    if not masks:
        return {
            "labels": [],
            "n_clusters": 0,
            "method": method,
            "cluster_sizes": {},
        }

    data = np.array([m.flatten().astype(np.float64) for m in masks])

    if method == "hierarchical":
        from sklearn.cluster import AgglomerativeClustering

        n_clusters = kwargs.get("n_clusters", 2)
        n_clusters = min(n_clusters, len(masks))
        clf = AgglomerativeClustering(n_clusters=n_clusters)
        labels = clf.fit_predict(data).tolist()

    elif method == "kmeans":
        from sklearn.cluster import KMeans

        n_clusters = kwargs.get("n_clusters", max(2, len(masks) // 2 + 1))
        n_clusters = min(n_clusters, len(masks))
        clf = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = clf.fit_predict(data).tolist()

    else:
        raise ValueError(f"Unknown method '{method}'. Use 'hierarchical' or 'kmeans'.")

    cluster_sizes = {}
    for lab in labels:
        cluster_sizes[lab] = cluster_sizes.get(lab, 0) + 1

    return {
        "labels": labels,
        "n_clusters": len(set(labels)),
        "method": method,
        "cluster_sizes": cluster_sizes,
    }


def compute_spectral_clusters(
    image: np.ndarray,
    n_clusters: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    """Spectral clustering on image pixels.

    Uses the RBF kernel affinity matrix for spectral embedding.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W, C)`` (must be multi-band).
    n_clusters : int
        Number of clusters.
    **kwargs
        ``gamma`` (float) – RBF kernel coefficient (default 1/n_features).

    Returns
    -------
    dict
        ``"labels"`` – label map ``(H, W)``,
        ``"eigenvalues"`` – Laplacian eigenvalues,
        ``"n_clusters"`` – number of clusters.
    """
    from sklearn.cluster import SpectralClustering

    if image.ndim == 2:
        raise ValueError("Spectral clustering requires a multi-band image (H, W, C).")

    h, w, c = image.shape
    data = image.reshape(-1, c).astype(np.float64)

    # Subsample for very large images to keep spectral clustering tractable
    max_pixels = kwargs.get("max_pixels", 50_000)
    if data.shape[0] > max_pixels:
        indices = np.random.default_rng(42).choice(data.shape[0], max_pixels, replace=False)
        sampled = data[indices]
    else:
        sampled = data
        indices = np.arange(data.shape[0])

    gamma = kwargs.get("gamma", 1.0 / c)
    n_clusters = min(n_clusters, sampled.shape[0])

    clf = SpectralClustering(
        n_clusters=n_clusters,
        affinity="rbf",
        gamma=gamma,
        random_state=42,
        n_init=3,
    )
    sampled_labels = clf.fit_predict(sampled)

    # Map back to full image
    labels = np.zeros(data.shape[0], dtype=np.int32)
    labels[indices] = sampled_labels

    return {
        "labels": labels.reshape(h, w),
        "eigenvalues": clf.eigenvalues_ if hasattr(clf, "eigenvalues_") else None,
        "n_clusters": n_clusters,
    }


def segment_by_threshold(
    image: np.ndarray,
    thresholds: list[float],
    **kwargs: Any,
) -> np.ndarray:
    """Segment image into regions by intensity thresholds.

    Parameters
    ----------
    image : np.ndarray
        Input image ``(H, W)`` (single-band).  For multi-band images the
        first band is used.
    thresholds : list of float
        Sorted list of threshold values.  ``n`` thresholds produce
        ``n+1`` segments.
    **kwargs
        ``bands_index`` (int) – band to use for multi-band images
        (default 0).

    Returns
    -------
    np.ndarray
        Label map ``(H, W)`` of int32 with segment ids ``0 … len(thresholds)``.
    """
    if image.ndim == 3:
        band_idx = kwargs.get("bands_index", 0)
        image = image[:, :, band_idx]

    image = image.astype(np.float64)
    thresholds = sorted(thresholds)

    label_map = np.zeros(image.shape, dtype=np.int32)
    for i, t in enumerate(thresholds):
        label_map[image > t] = i + 1

    return label_map


def compute_cluster_stats(
    clustered: np.ndarray,
    image: np.ndarray,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute per-cluster statistics.

    Parameters
    ----------
    clustered : np.ndarray
        Label map ``(H, W)`` with integer cluster ids.
    image : np.ndarray
        Source image ``(H, W)`` or ``(H, W, C)``.
    **kwargs
        ``percentiles`` (list of float) – percentiles to compute
        (default [10, 25, 50, 75, 90]).

    Returns
    -------
    dict
        Mapping from cluster id to a dict of statistics (``count``,
        ``mean``, ``std``, ``min``, ``max``, ``percentiles``).
    """
    percentiles = kwargs.get("percentiles", [10, 25, 50, 75, 90])
    unique_labels = np.unique(clustered)

    stats: dict[int, dict[str, Any]] = {}
    for label_id in unique_labels:
        mask = clustered == label_id
        if image.ndim == 2:
            pixels = image[mask]
        else:
            pixels = image[mask].reshape(-1, image.shape[-1])

        flat = pixels.astype(np.float64)
        pct_values = np.percentile(flat, percentiles, axis=0)

        stats[int(label_id)] = {
            "count": int(np.sum(mask)),
            "mean": float(np.mean(flat, axis=0)) if flat.ndim == 1 else np.mean(flat, axis=0).tolist(),
            "std": float(np.std(flat, axis=0)) if flat.ndim == 1 else np.std(flat, axis=0).tolist(),
            "min": float(np.min(flat)) if flat.ndim == 1 else np.min(flat, axis=0).tolist(),
            "max": float(np.max(flat)) if flat.ndim == 1 else np.max(flat, axis=0).tolist(),
            "percentiles": {
                int(p): (float(v) if flat.ndim == 1 else v.tolist()) for p, v in zip(percentiles, pct_values)
            },
        }

    return stats


def merge_clusters(
    labels: np.ndarray,
    merge_map: dict[int, int],
) -> np.ndarray:
    """Merge cluster labels according to a mapping.

    Parameters
    ----------
    labels : np.ndarray
        Label map ``(H, W)``.
    merge_map : dict
        Mapping ``{old_label: new_label}``.  Labels not present in the
        map are kept unchanged.

    Returns
    -------
    np.ndarray
        Merged label map with the same dtype as *labels*.
    """
    merged = labels.copy()
    for old_label, new_label in merge_map.items():
        merged[labels == old_label] = new_label
    return merged


def silhouette_score(
    labels: np.ndarray,
    data: np.ndarray,
    sample_size: int = 10_000,
    random_state: int = 42,
) -> float:
    """Compute the silhouette clustering quality score.

    Parameters
    ----------
    labels : np.ndarray
        Cluster labels flattened or reshaped to match *data*.
    data : np.ndarray
        Feature array ``(N, D)`` or image ``(H, W, C)`` that was
        clustered.
    sample_size : int
        Maximum number of samples used (silhouette is expensive on
        large datasets).
    random_state : int
        Random seed for subsampling.

    Returns
    -------
    float
        Mean silhouette coefficient in ``[-1, 1]``.  Higher is better.
    """
    from sklearn.metrics import silhouette_score as _sk_silhouette

    labels_flat = np.asarray(labels).flatten()
    data_flat = np.asarray(data).reshape(len(labels_flat), -1)

    n_unique = len(set(labels_flat.tolist()))
    if n_unique < 2:
        return 0.0

    if len(labels_flat) > sample_size:
        rng = np.random.default_rng(random_state)
        idx = rng.choice(len(labels_flat), sample_size, replace=False)
        labels_flat = labels_flat[idx]
        data_flat = data_flat[idx]

    return float(_sk_silhouette(data_flat, labels_flat))
