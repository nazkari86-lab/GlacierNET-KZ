#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uncertainty Quantification Module for GlacierNET-KZ.

Provides MC-Dropout inference, ensemble variance, test-time augmentation (TTA),
calibration metrics (ECE, MCE, Brier), and uncertainty decomposition
(epistemic vs aleatoric) for glacier segmentation predictions.

Dual-backend: tries cv2 first, falls back to scipy.ndimage for image ops.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

__all__ = [
    "mcdropout_predict",
    "ensemble_uncertainty",
    "tta_uncertainty",
    "calibration_metrics",
    "compute_prediction_entropy",
    "compute_mutual_information",
    "uncertainty_to_confidence",
    "apply_uncertainty_threshold",
]

# ---------------------------------------------------------------------------
# Dual-backend: cv2 first, scipy fallback for affine / geometric transforms
# ---------------------------------------------------------------------------

_HAS_CV2 = False
try:
    import cv2

    _HAS_CV2 = True
except ImportError:
    pass

if not _HAS_CV2:
    try:
        from scipy.ndimage import (
            rotate as _scipy_rotate,
        )
        from scipy.ndimage import (
            shift as _scipy_shift,
        )
        from scipy.ndimage import (
            zoom as _scipy_zoom,
        )
    except ImportError:
        _scipy_rotate = None
        _scipy_shift = None
        _scipy_zoom = None

# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------


def _resize(
    image: np.ndarray,
    target_h: int,
    target_w: int,
    interpolation: int = 1,
) -> np.ndarray:
    """Resize *image* to (*target_h*, *target_w*) using available backend."""
    if _HAS_CV2:
        interp = interpolation
        return cv2.resize(image, (target_w, target_h), interpolation=interp)
    # scipy fallback – nearest-neighbour via zoom
    if image.ndim == 2:
        zoom_h = target_h / image.shape[0]
        zoom_w = target_w / image.shape[1]
        if _scipy_zoom is not None:
            return _scipy_zoom(image, (zoom_h, zoom_w), order=0).astype(image.dtype)
    # last resort: numpy indexing
    idx_h = np.linspace(0, image.shape[0] - 1, target_h).astype(int)
    idx_w = np.linspace(0, image.shape[1] - 1, target_w).astype(int)
    return image[np.ix_(idx_h, idx_w)]


def _flip_h(image: np.ndarray) -> np.ndarray:
    """Horizontal flip."""
    if _HAS_CV2:
        return cv2.flip(image, 1)
    return np.flip(image, axis=1).copy()


def _flip_v(image: np.ndarray) -> np.ndarray:
    """Vertical flip."""
    if _HAS_CV2:
        return cv2.flip(image, 0)
    return np.flip(image, axis=0).copy()


def _rotate90(image: np.ndarray, k: int = 1) -> np.ndarray:
    """Rotate by k * 90 degrees counter-clockwise."""
    return np.rot90(image, k=k).copy()


# ---------------------------------------------------------------------------
# Core uncertainty functions
# ---------------------------------------------------------------------------


def compute_prediction_entropy(prediction: np.ndarray) -> np.ndarray:
    """Compute Shannon entropy of a softmax prediction map.

    Parameters
    ----------
    prediction : np.ndarray, float32
        Prediction map of shape ``(C, H, W)`` or ``(H, W)`` for binary case.
        Values should sum to ~1 along channel axis after softmax.

    Returns
    -------
    np.ndarray
        Per-pixel entropy of shape ``(H, W)``.
    """
    prediction = prediction.astype(np.float64)
    if prediction.ndim == 2:
        # binary: interpret as p(class=1)
        p = np.clip(prediction, 1e-12, 1.0 - 1e-12)
        entropy = -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p))
        return entropy.astype(np.float32)
    # multi-class
    p = np.clip(prediction, 1e-12, 1.0)
    entropy = -np.sum(p * np.log(p), axis=0)
    return entropy.astype(np.float32)


def compute_mutual_information(predictions: List[np.ndarray]) -> np.ndarray:
    """Compute ensemble mutual information (a proxy for epistemic uncertainty).

    MI = H(mean) - mean(H(x_i))

    Parameters
    ----------
    predictions : list of np.ndarray
        List of prediction maps, each ``(C, H, W)`` or ``(H, W)``.

    Returns
    -------
    np.ndarray
        Per-pixel mutual information of shape ``(H, W)``.
    """
    if len(predictions) == 0:
        raise ValueError("predictions list must not be empty")

    stack = np.stack([p.astype(np.float64) for p in predictions], axis=0)  # (N, C, H, W) or (N, H, W)
    mean_pred = np.mean(stack, axis=0)

    h_mean = compute_prediction_entropy(mean_pred.astype(np.float32))

    h_individual = np.stack(
        [compute_prediction_entropy(p.astype(np.float32)) for p in predictions],
        axis=0,
    )
    mean_h_individual = np.mean(h_individual, axis=0)

    mi = h_mean - mean_h_individual
    return np.clip(mi, 0.0, None).astype(np.float32)


def uncertainty_to_confidence(uncertainty_map: np.ndarray) -> np.ndarray:
    """Convert an uncertainty map to a confidence map in [0, 1].

    Simple linear transform: ``confidence = 1 - uncertainty``.

    Parameters
    ----------
    uncertainty_map : np.ndarray, float32
        Uncertainty values, expected in [0, 1].

    Returns
    -------
    np.ndarray
        Confidence map, same shape.
    """
    return (1.0 - uncertainty_map).clip(0.0, 1.0).astype(np.float32)


def apply_uncertainty_threshold(
    uncertainty_map: np.ndarray,
    threshold: float = 0.3,
) -> np.ndarray:
    """Create a binary mask where pixels exceed the uncertainty threshold.

    Parameters
    ----------
    uncertainty_map : np.ndarray, float32
        Per-pixel uncertainty.
    threshold : float
        Threshold above which pixels are flagged.

    Returns
    -------
    np.ndarray
        Boolean mask of shape ``(H, W)``.
    """
    return (uncertainty_map > threshold).astype(bool)


# ---------------------------------------------------------------------------
# MC-Dropout
# ---------------------------------------------------------------------------


def mcdropout_predict(
    model: Any,
    image: np.ndarray,
    n_samples: int = 30,
    dropout_rate: float = 0.1,
) -> Dict[str, np.ndarray]:
    """Run Monte Carlo Dropout inference for uncertainty estimation.

    Enables dropout at inference time and runs *n_samples* forward passes.
    Decomposes total uncertainty into epistemic (model) and aleatoric (data).

    Parameters
    ----------
    model : callable
        Model with ``model.training`` flag and ``model(x, training=True)``
        signature (Keras / TF / PyTorch via wrapper).  Must accept an
        ``image`` of shape ``(1, H, W, C)`` or ``(C, H, W)`` and return a
        softmax probability map.
    image : np.ndarray, float32
        Single input image, shape ``(H, W, C)`` or ``(C, H, W)``.
    n_samples : int
        Number of stochastic forward passes.
    dropout_rate : float
        Expected dropout rate (used in analytic decomposition).

    Returns
    -------
    dict
        ``mean_prediction`` : np.ndarray, float32 – average prediction.
        ``uncertainty_map`` : np.ndarray, float32 – total predictive variance.
        ``epistemic_uncertainty`` : np.ndarray, float32 – model uncertainty.
        ``aleatoric_uncertainty`` : np.ndarray, float32 – data uncertainty.
        ``prediction_entropy`` : np.ndarray, float32 – entropy of mean pred.
    """
    # Ensure batch dim
    if image.ndim == 3:
        img = np.expand_dims(image, axis=0)
    else:
        img = image

    samples: List[np.ndarray] = []
    for _ in range(n_samples):
        pred = model(img, training=True)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        pred = np.asarray(pred, dtype=np.float64)
        # squeeze batch dim if present
        if pred.ndim == 4:
            pred = pred[0]
        samples.append(pred)

    stack = np.stack(samples, axis=0)  # (N, C, H, W) or (N, H, W)
    mean_pred = np.mean(stack, axis=0).astype(np.float32)

    # Kendall & Gal (2017) decomposition for binary Bernoulli output:
    # epistemic  = Var[E[p]]   = variance of the mean predictions across passes
    # aleatoric  = E[Var[p]]   = mean of per-sample p*(1-p)  (Bernoulli variance)
    # total_var  = epistemic + aleatoric  (law of total variance)
    epistemic = np.var(stack, axis=0).astype(np.float32)
    aleatoric = np.mean(stack * (1.0 - stack), axis=0).astype(np.float32)
    total_var = (epistemic + aleatoric).astype(np.float32)

    pred_entropy = compute_prediction_entropy(mean_pred)

    return {
        "mean_prediction": mean_pred,
        "uncertainty_map": total_var.astype(np.float32),
        "epistemic_uncertainty": epistemic,
        "aleatoric_uncertainty": aleatoric,
        "prediction_entropy": pred_entropy,
    }


# ---------------------------------------------------------------------------
# Ensemble uncertainty
# ---------------------------------------------------------------------------


def ensemble_uncertainty(
    models: List[Any],
    image: np.ndarray,
) -> Dict[str, np.ndarray]:
    """Compute uncertainty from an ensemble of models.

    Parameters
    ----------
    models : list of callable
        Each model accepts an image and returns a softmax prediction.
    image : np.ndarray, float32
        Single input image, shape ``(H, W, C)`` or ``(C, H, W)``.

    Returns
    -------
    dict
        ``mean_prediction`` : np.ndarray – ensemble mean prediction.
        ``variance`` : np.ndarray – pixel-wise variance across models.
        ``model_disagreement`` : np.ndarray – max disagreement (max - min
            of per-class mean).
        ``confidence`` : np.ndarray – confidence derived from ensemble variance.
    """
    if not models:
        raise ValueError("models list must not be empty")

    if image.ndim == 3:
        img = np.expand_dims(image, axis=0)
    else:
        img = image

    preds: List[np.ndarray] = []
    for m in models:
        p = m(img, training=False)
        if isinstance(p, (list, tuple)):
            p = p[0]
        p = np.asarray(p, dtype=np.float64)
        if p.ndim == 4:
            p = p[0]
        preds.append(p)

    stack = np.stack(preds, axis=0)
    mean_pred = np.mean(stack, axis=0).astype(np.float32)
    variance = np.var(stack, axis=0).astype(np.float32)

    # model_disagreement: per-pixel range (max - min) across models
    model_disagreement = (np.max(stack, axis=0) - np.min(stack, axis=0)).astype(np.float32)

    # confidence from mutual information
    mi = compute_mutual_information([p.astype(np.float32) for p in preds])
    confidence = uncertainty_to_confidence(mi)

    return {
        "mean_prediction": mean_pred,
        "variance": variance,
        "model_disagreement": model_disagreement,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Test-Time Augmentation (TTA)
# ---------------------------------------------------------------------------

_TTA_AUGMENTATIONS = [
    "identity",
    "flip_h",
    "flip_v",
    "rot90",
    "rot180",
    "rot270",
]


def _augment(image: np.ndarray, aug_name: str) -> Tuple[np.ndarray, callable]:
    """Apply augmentation and return the inverse function.

    Returns (augmented_image, inverse_fn) where inverse_fn maps a prediction
    back to the original spatial layout.
    """
    if aug_name == "identity":
        return image, lambda x: x
    if aug_name == "flip_h":
        return _flip_h(image), lambda x: _flip_h(x)
    if aug_name == "flip_v":
        return _flip_v(image), lambda x: _flip_v(x)
    if aug_name == "rot90":
        return _rotate90(image, k=1), lambda x: _rotate90(x, k=-1 % 4)
    if aug_name == "rot180":
        return _rotate90(image, k=2), lambda x: _rotate90(x, k=-2 % 4)
    if aug_name == "rot270":
        return _rotate90(image, k=3), lambda x: _rotate90(x, k=-3 % 4)
    raise ValueError(f"Unknown augmentation: {aug_name}")


def tta_uncertainty(
    model: Any,
    image: np.ndarray,
    n_augmentations: int = 5,
) -> Dict[str, Any]:
    """Run test-time augmentation and measure prediction variance.

    Applies random augmentations, runs inference, and inverts each
    prediction back to the original coordinate system.

    Parameters
    ----------
    model : callable
        Model accepting a batched image and returning softmax predictions.
    image : np.ndarray, float32
        Input image ``(H, W, C)`` or ``(C, H, W)``.
    n_augmentations : int
        Number of augmented forward passes (beyond the identity pass).

    Returns
    -------
    dict
        ``mean_prediction`` : np.ndarray – mean across all augmented predictions.
        ``augmented_predictions`` : list of np.ndarray – individual predictions.
        ``tta_variance`` : np.ndarray – pixel-wise variance across augmentations.
    """
    if image.ndim == 3:
        img = np.expand_dims(image, axis=0)
    else:
        img = image

    n_total = n_augmentations + 1  # include identity
    available = list(_TTA_AUGMENTATIONS)
    rng = np.random.default_rng()
    chosen = rng.choice(available, size=min(n_total, len(available)), replace=False).tolist()
    # Ensure identity is always present
    if "identity" not in chosen:
        chosen[0] = "identity"

    aug_preds: List[np.ndarray] = []
    for aug_name in chosen[:n_total]:
        aug_img, inv_fn = _augment(img[0], aug_name)
        batch = np.expand_dims(aug_img, axis=0)
        pred = model(batch, training=False)
        if isinstance(pred, (list, tuple)):
            pred = pred[0]
        pred = np.asarray(pred, dtype=np.float64)
        if pred.ndim == 4:
            pred = pred[0]
        # invert spatial augmentation
        inv_pred = inv_fn(pred)
        aug_preds.append(inv_pred.astype(np.float32))

    mean_pred = np.mean(np.stack(aug_preds, axis=0), axis=0).astype(np.float32)
    tta_var = np.var(np.stack(aug_preds, axis=0), axis=0).astype(np.float32)

    return {
        "mean_prediction": mean_pred,
        "augmented_predictions": aug_preds,
        "tta_variance": tta_var,
    }


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------


def calibration_metrics(
    predictions: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, Any]:
    """Compute calibration metrics for probabilistic predictions.

    Parameters
    ----------
    predictions : np.ndarray, float32
        Predicted probabilities.  For binary: ``(H, W)`` with ``p(class=1)``.
        For multi-class: ``(C, H, W)``.
    labels : np.ndarray
        Ground-truth labels, same spatial shape.  For binary: 0/1.
        For multi-class: integer class indices.
    n_bins : int
        Number of bins for ECE / MCE.

    Returns
    -------
    dict
        ``expected_calibration_error`` : float
        ``maximum_calibration_error`` : float
        ``brier_score`` : float
        ``reliability_diagram_data`` : dict with ``bin_confidences``,
        ``bin_accuracies``, ``bin_counts``, ``bin_boundaries``.
    """
    predictions = predictions.astype(np.float64)
    labels = labels.astype(np.int64)

    # Binary case
    if predictions.ndim == 2 or (predictions.ndim == 3 and predictions.shape[0] == 1):
        if predictions.ndim == 3:
            probs = predictions[0]
        else:
            probs = predictions
        binary_labels = (labels > 0).astype(np.int64)

        return _binary_calibration(probs, binary_labels, n_bins)

    # Multi-class
    n_classes = predictions.shape[0]
    flat_probs = predictions.reshape(n_classes, -1).T  # (H*W, C)
    flat_labels = labels.ravel()

    confidences = np.max(flat_probs, axis=1)
    predictions_argmax = np.argmax(flat_probs, axis=1)
    accuracies = (predictions_argmax == flat_labels).astype(np.float64)

    return _general_calibration(confidences, accuracies, flat_probs, flat_labels, n_classes, n_bins)


def _binary_calibration(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int,
) -> Dict[str, Any]:
    """Calibration metrics for binary predictions."""
    flat_p = probs.ravel()
    flat_l = labels.ravel()
    confidences = flat_p
    accuracies = flat_l.astype(np.float64)

    return _general_calibration(confidences, accuracies, flat_p.reshape(-1, 1), flat_l, 2, n_bins)


def _general_calibration(
    confidences: np.ndarray,
    accuracies: np.ndarray,
    flat_probs: np.ndarray,
    flat_labels: np.ndarray,
    n_classes: int,
    n_bins: int,
) -> Dict[str, Any]:
    """Shared calibration computation for binary and multi-class."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_confidences = np.zeros(n_bins, dtype=np.float64)
    bin_accuracies = np.zeros(n_bins, dtype=np.float64)
    bin_counts = np.zeros(n_bins, dtype=np.int64)

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (confidences >= lo) & (confidences < hi)
        if i == n_bins - 1:
            mask = mask | (confidences == hi)  # include right edge for last bin
        cnt = np.sum(mask)
        bin_counts[i] = cnt
        if cnt > 0:
            bin_confidences[i] = np.mean(confidences[mask])
            bin_accuracies[i] = np.mean(accuracies[mask])

    total = confidences.shape[0]
    weights = bin_counts / total if total > 0 else bin_counts

    ece = float(np.sum(weights * np.abs(bin_accuracies - bin_confidences)))
    mce = float(np.max(np.abs(bin_accuracies - bin_confidences)) if total > 0 else 0.0)

    # Brier score: mean squared error of probabilistic predictions
    if n_classes == 2 and flat_probs.shape[1] == 1:
        brier = float(np.mean((flat_probs.ravel() - flat_labels.astype(np.float64)) ** 2))
    else:
        one_hot = np.zeros((flat_labels.shape[0], n_classes), dtype=np.float64)
        valid = (flat_labels >= 0) & (flat_labels < n_classes)
        one_hot[valid, flat_labels[valid]] = 1.0
        brier = float(np.mean(np.sum((flat_probs - one_hot) ** 2, axis=1)))

    return {
        "expected_calibration_error": ece,
        "maximum_calibration_error": mce,
        "brier_score": brier,
        "reliability_diagram_data": {
            "bin_confidences": bin_confidences.tolist(),
            "bin_accuracies": bin_accuracies.tolist(),
            "bin_counts": bin_counts.tolist(),
            "bin_boundaries": bin_edges.tolist(),
        },
    }
