#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model evaluation module for GlacierNET-KZ.

Provides pixel-level metrics (IoU, Dice, Precision, Recall, F1, Accuracy,
Specificity), region-level metrics, threshold sweeps, ROC/PR curves,
confusion matrices, and batch evaluation utilities.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd

try:
    import cv2

    _cv2_available = True
except ImportError:
    _cv2_available = False

from scipy import ndimage

__all__ = [
    "compute_pixel_metrics",
    "compute_region_metrics",
    "threshold_sweep",
    "compute_roc_curve",
    "compute_pr_curve",
    "confusion_matrix",
    "evaluate_model",
    "compare_models",
    "cross_validate",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _binarise(arr: np.ndarray, threshold: float) -> np.ndarray:
    """Return a boolean binary mask."""
    return np.asarray(arr, dtype=np.float64) >= threshold


def _find_contours(mask: np.ndarray) -> list:
    """Return contours from a uint8 binary mask, using cv2 or scipy fallback."""
    mask_uint8 = mask.astype(np.uint8)
    if _cv2_available:
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return contours
    # scipy fallback: use label-based contour approximation
    labelled, num_features = ndimage.label(mask_uint8)
    contours = []
    for i in range(1, num_features + 1):
        region_mask = (labelled == i).astype(np.uint8)
        np.argwhere(region_mask)
        # approximate contour as the boundary pixels
        dilated = ndimage.binary_dilation(region_mask)
        boundary = dilated ^ region_mask
        contours.append(np.argwhere(boundary))
    return contours


def _centroid(mask: np.ndarray) -> tuple[float, float]:
    """Compute centroid (row, col) of a binary mask."""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return (float("nan"), float("nan"))
    return (float(np.mean(ys)), float(np.mean(xs)))


# ---------------------------------------------------------------------------
# Pixel-level metrics
# ---------------------------------------------------------------------------


def compute_pixel_metrics(pred: np.ndarray, true: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    """Compute pixel-level segmentation metrics.

    Parameters
    ----------
    pred : np.ndarray
        Predicted probability map or binary mask.
    true : np.ndarray
        Ground-truth binary mask.
    threshold : float
        Binarisation threshold for *pred*.

    Returns
    -------
    dict[str, float]
        Dictionary with keys: iou, dice, precision, recall, f1, accuracy,
        specificity.
    """
    pred_bin = _binarise(pred, threshold)
    true_bin = _binarise(true, 0.5)

    tp = float(np.sum(pred_bin & true_bin))
    fp = float(np.sum(pred_bin & ~true_bin))
    fn = float(np.sum(~pred_bin & true_bin))
    tn = float(np.sum(~pred_bin & ~true_bin))

    eps = 1e-12
    precision = tp / (tp + fp + eps)
    recall = tp / (tp + fn + eps)
    f1 = 2 * precision * recall / (precision + recall + eps)
    iou = tp / (tp + fp + fn + eps)
    accuracy = (tp + tn) / (tp + fp + fn + tn + eps)
    specificity = tn / (tn + fp + eps)

    return {
        "iou": iou,
        "dice": f1,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "specificity": specificity,
    }


# ---------------------------------------------------------------------------
# Region-level metrics
# ---------------------------------------------------------------------------


def compute_region_metrics(pred: np.ndarray, true: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    """Compute region-level segmentation metrics.

    Parameters
    ----------
    pred : np.ndarray
        Predicted probability map or binary mask.
    true : np.ndarray
        Ground-truth binary mask.
    threshold : float
        Binarisation threshold for *pred*.

    Returns
    -------
    dict[str, float]
        area_ratio, perimeter_ratio, centroid_distance, num_regions,
        fragmentation_index.
    """
    pred_bin = _binarise(pred, threshold).astype(np.uint8)
    true_bin = _binarise(true, 0.5).astype(np.uint8)

    # area ratio
    pred_area = float(np.sum(pred_bin))
    true_area = float(np.sum(true_bin))
    area_ratio = pred_area / (true_area + 1e-12)

    # perimeter via contours
    pred_contours = _find_contours(pred_bin)
    true_contours = _find_contours(true_bin)

    if _cv2_available:
        pred_perim = sum(cv2.arcLength(c, closed=True) for c in pred_contours) if pred_contours else 0.0
        true_perim = sum(cv2.arcLength(c, closed=True) for c in true_contours) if true_contours else 0.0
    else:
        pred_perim = float(sum(len(c) for c in pred_contours))
        true_perim = float(sum(len(c) for c in true_contours))

    perimeter_ratio = pred_perim / (true_perim + 1e-12)

    # centroid distance
    pred_c = _centroid(pred_bin)
    true_c = _centroid(true_bin)
    centroid_distance = float(np.sqrt((pred_c[0] - true_c[0]) ** 2 + (pred_c[1] - true_c[1]) ** 2))

    # number of regions
    pred_labelled, pred_n = ndimage.label(pred_bin)
    true_labelled, true_n = ndimage.label(true_bin)

    # fragmentation index: ratio of component count to true count
    fragmentation_index = float(pred_n / (true_n + 1e-12))

    return {
        "area_ratio": area_ratio,
        "perimeter_ratio": perimeter_ratio,
        "centroid_distance": centroid_distance,
        "num_regions": float(pred_n),
        "fragmentation_index": fragmentation_index,
    }


# ---------------------------------------------------------------------------
# Threshold sweep
# ---------------------------------------------------------------------------


def threshold_sweep(
    pred: np.ndarray,
    true: np.ndarray,
    thresholds: Sequence[float] | None = None,
) -> list[dict[str, float]]:
    """Evaluate pixel metrics across a range of thresholds.

    Parameters
    ----------
    pred : np.ndarray
        Predicted probability map.
    true : np.ndarray
        Ground-truth binary mask.
    thresholds : Sequence[float] | None
        Thresholds to evaluate. Defaults to 20 evenly spaced values in [0, 1].

    Returns
    -------
    list[dict[str, float]]
        One dict per threshold containing 'threshold' and all pixel metrics.
    """
    if thresholds is None:
        thresholds = np.linspace(0.0, 1.0, 21).tolist()

    results = []
    for thr in thresholds:
        metrics = compute_pixel_metrics(pred, true, threshold=thr)
        metrics["threshold"] = thr
        results.append(metrics)
    return results


# ---------------------------------------------------------------------------
# ROC curve
# ---------------------------------------------------------------------------


def compute_roc_curve(scores: np.ndarray, labels: np.ndarray) -> dict[str, np.ndarray]:
    """Compute ROC curve and AUC from continuous scores and binary labels.

    Parameters
    ----------
    scores : np.ndarray
        Continuous prediction scores (higher = more likely positive).
    labels : np.ndarray
        Binary ground-truth labels.

    Returns
    -------
    dict[str, np.ndarray]
        fpr, tpr, auc, thresholds.
    """
    scores = np.asarray(scores, dtype=np.float64).ravel()
    labels = np.asarray(labels, dtype=np.float64).ravel()

    # Sort by decreasing score
    order = np.argsort(-scores, kind="mergesort")
    scores_sorted = scores[order]
    labels_sorted = labels[order]

    # Unique thresholds (descending)
    thresholds = np.unique(scores_sorted)[::-1]

    tprs: list[float] = []
    fprs: list[float] = []

    total_pos = float(np.sum(labels == 1))
    total_neg = float(np.sum(labels == 0))

    for thr in thresholds:
        pred_pos = scores_sorted >= thr
        tp = float(np.sum((pred_pos) & (labels_sorted == 1)))
        fp = float(np.sum((pred_pos) & (labels_sorted == 0)))
        tprs.append(tp / (total_pos + 1e-12))
        fprs.append(fp / (total_neg + 1e-12))

    tprs = np.array([0.0] + tprs + [1.0])
    fprs = np.array([0.0] + fprs + [1.0])
    thresholds_arr = np.array([scores_sorted[0] + 1e-9] + list(thresholds) + [scores_sorted[-1] - 1e-9])

    # AUC via trapezoidal rule
    sorted_idx = np.argsort(fprs)
    fprs_sorted = fprs[sorted_idx]
    tprs_sorted = tprs[sorted_idx]
    auc = float(np.trapz(tprs_sorted, fprs_sorted))

    return {"fpr": fprs_sorted, "tpr": tprs_sorted, "auc": auc, "thresholds": thresholds_arr[sorted_idx]}


# ---------------------------------------------------------------------------
# PR curve
# ---------------------------------------------------------------------------


def compute_pr_curve(scores: np.ndarray, labels: np.ndarray) -> dict[str, np.ndarray]:
    """Compute Precision-Recall curve and Average Precision.

    Parameters
    ----------
    scores : np.ndarray
        Continuous prediction scores.
    labels : np.ndarray
        Binary ground-truth labels.

    Returns
    -------
    dict[str, np.ndarray]
        precision, recall, f1, thresholds, average_precision.
    """
    scores = np.asarray(scores, dtype=np.float64).ravel()
    labels = np.asarray(labels, dtype=np.float64).ravel()

    order = np.argsort(-scores, kind="mergesort")
    scores_sorted = scores[order]
    labels_sorted = labels[order]

    thresholds = np.unique(scores_sorted)[::-1]

    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    total_pos = float(np.sum(labels == 1))

    for thr in thresholds:
        pred_pos = scores_sorted >= thr
        tp = float(np.sum(pred_pos & (labels_sorted == 1)))
        fp = float(np.sum(pred_pos & (labels_sorted == 0)))
        precision = tp / (tp + fp + 1e-12)
        recall = tp / (total_pos + 1e-12)
        f1 = 2 * precision * recall / (precision + recall + 1e-12)
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    # Prepend (recall=0, precision=1) point
    recalls = [0.0] + recalls
    precisions = [1.0] + precisions
    f1s = [0.0] + f1s
    thresholds_arr = np.array([scores_sorted[0] + 1e-9] + list(thresholds))

    precisions_arr = np.array(precisions)
    recalls_arr = np.array(recalls)

    # Average precision = area under PR curve
    average_precision = float(np.trapz(precisions_arr, recalls_arr))

    return {
        "precision": precisions_arr,
        "recall": recalls_arr,
        "f1": np.array(f1s),
        "thresholds": thresholds_arr,
        "average_precision": average_precision,
    }


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------


def confusion_matrix(pred: np.ndarray, true: np.ndarray, threshold: float = 0.5) -> dict[str, int]:
    """Compute confusion matrix counts.

    Parameters
    ----------
    pred : np.ndarray
        Predicted probability map or binary mask.
    true : np.ndarray
        Ground-truth binary mask.
    threshold : float
        Binarisation threshold for *pred*.

    Returns
    -------
    dict[str, int]
        tp, fp, fn, tn.
    """
    pred_bin = _binarise(pred, threshold)
    true_bin = _binarise(true, 0.5)

    tp = int(np.sum(pred_bin & true_bin))
    fp = int(np.sum(pred_bin & ~true_bin))
    fn = int(np.sum(~pred_bin & true_bin))
    tn = int(np.sum(~pred_bin & ~true_bin))

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


# ---------------------------------------------------------------------------
# Full-model evaluation
# ---------------------------------------------------------------------------


def evaluate_model(
    model: Any,
    test_generator: Any,
    metrics: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run a trained model over a data generator and aggregate metrics.

    Parameters
    ----------
    model : Any
        A Keras-style model with ``.predict(x)`` returning a numpy array.
    test_generator : Any
        Generator that yields ``(images, masks)`` batches.
    metrics : Sequence[str] | None
        Subset of metric families to compute.  Accepts any of:
        ``'pixel'``, ``'region'``, ``'confusion'``.
        Defaults to all three.

    Returns
    -------
    dict[str, Any]
        Aggregated metric averages plus per-sample detail.
    """
    if metrics is None:
        metrics = ("pixel", "region", "confusion")

    all_pixel: list[dict[str, float]] = []
    all_region: list[dict[str, float]] = []
    all_conf: list[dict[str, int]] = []

    for batch_images, batch_masks in test_generator:
        preds = np.asarray(model.predict(batch_images, verbose=0))
        batch_masks = np.asarray(batch_masks)

        for i in range(preds.shape[0]):
            p = preds[i]
            t = batch_masks[i]

            # collapse channel dim if present
            if p.ndim == 3:
                p = p[..., 0]
            if t.ndim == 3:
                t = t[..., 0]

            if "pixel" in metrics:
                all_pixel.append(compute_pixel_metrics(p, t))
            if "region" in metrics:
                all_region.append(compute_region_metrics(p, t))
            if "confusion" in metrics:
                all_conf.append(confusion_matrix(p, t))

    results: dict[str, Any] = {"sample_count": len(all_pixel)}

    if all_pixel:
        results["pixel"] = {k: float(np.mean([d[k] for d in all_pixel])) for k in all_pixel[0]}
    if all_region:
        results["region"] = {k: float(np.mean([d[k] for d in all_region])) for k in all_region[0]}
    if all_conf:
        sums = {k: sum(d[k] for d in all_conf) for k in all_conf[0]}
        results["confusion"] = sums
        tp, fp, fn, tn = sums["tp"], sums["fp"], sums["fn"], sums["tn"]
        eps = 1e-12
        results["pixel_from_confusion"] = {
            "precision": tp / (tp + fp + eps),
            "recall": tp / (tp + fn + eps),
            "f1": 2 * tp / (2 * tp + fp + fn + eps),
            "accuracy": (tp + tn) / (tp + fp + fn + tn + eps),
        }

    results["per_sample_pixel"] = all_pixel
    results["per_sample_region"] = all_region
    return results


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------


def compare_models(
    models: list[Any],
    test_generator: Any,
    names: list[str] | None = None,
) -> pd.DataFrame:
    """Compare multiple models side-by-side on the same test set.

    Parameters
    ----------
    models : list[Any]
        Models with a ``.predict()`` interface.
    test_generator : Any
        Data generator to evaluate on.
    names : list[str] | None
        Human-readable model names.  Defaults to ``Model 1``, ``Model 2``, ...

    Returns
    -------
    pd.DataFrame
        Rows = models, columns = aggregated metric values.
    """
    if names is None:
        names = [f"Model {i + 1}" for i in range(len(models))]

    rows = []
    for model, name in zip(models, names):
        res = evaluate_model(model, test_generator)
        row = {"model": name, "samples": res["sample_count"]}
        for family in ("pixel", "region", "pixel_from_confusion"):
            if family in res:
                for k, v in res[family].items():
                    row[f"{family}_{k}"] = v
        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# K-fold cross-validation
# ---------------------------------------------------------------------------


def cross_validate(
    model_builder: Callable[[], Any],
    data: tuple[np.ndarray, np.ndarray],
    k: int = 5,
) -> dict[str, Any]:
    """Run k-fold cross-validation and aggregate per-fold metrics.

    Parameters
    ----------
    model_builder : Callable[[], Any]
        Zero-argument callable that returns a fresh, untrained model.
    data : tuple[np.ndarray, np.ndarray]
        ``(images, masks)`` arrays.
    k : int
        Number of folds.

    Returns
    -------
    dict[str, Any]
        Per-fold pixel metrics and mean/std summary.
    """
    images, masks = data
    n = images.shape[0]
    indices = np.arange(n)
    np.random.shuffle(indices)

    folds = np.array_split(indices, k)
    fold_results: list[dict[str, float]] = []

    for fold_idx, val_idx in enumerate(folds):
        train_idx = np.setdiff1d(indices, val_idx)
        train_x, train_y = images[train_idx], masks[train_idx]
        val_x, val_y = images[val_idx], masks[val_idx]

        model = model_builder()
        model.fit(train_x, train_y, verbose=0)

        preds = np.asarray(model.predict(val_x, verbose=0))

        # collapse channels
        if preds.ndim == 4:
            preds = preds[..., 0]
        if val_y.ndim == 4:
            val_y = val_y[..., 0]

        metrics_per_sample = [compute_pixel_metrics(preds[i], val_y[i]) for i in range(preds.shape[0])]
        avg = {k: float(np.mean([m[k] for m in metrics_per_sample])) for k in metrics_per_sample[0]}
        avg["fold"] = fold_idx
        fold_results.append(avg)

    # summary
    summary = {
        "fold_results": fold_results,
        "mean": {k: float(np.mean([f[k] for f in fold_results])) for k in fold_results[0] if k != "fold"},
        "std": {k: float(np.std([f[k] for f in fold_results])) for k in fold_results[0] if k != "fold"},
    }
    return summary
