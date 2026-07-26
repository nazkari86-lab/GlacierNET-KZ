"""Scientifically comparable metrics for GlacierNET-KZ benchmark v2.

All overlap metrics in this module are computed from the same thresholded
prediction. Boundary distances are reported in physical units when
``pixel_size`` is expressed in metres.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np
from scipy import ndimage


def _validated_masks(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    true = np.asarray(y_true)
    prob = np.asarray(y_prob, dtype=np.float64)
    if true.shape != prob.shape:
        raise ValueError(f"shape mismatch: y_true={true.shape}, y_prob={prob.shape}")
    if true.size == 0:
        raise ValueError("masks must not be empty")
    if not np.isfinite(prob).all():
        raise ValueError("y_prob contains NaN or infinity")
    true_values = np.unique(true)
    if not np.isin(true_values, [0, 1, False, True]).all():
        raise ValueError("y_true must be binary")
    return true.astype(bool), prob >= threshold


def hard_segmentation_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, float | int]:
    """Return one internally consistent hard confusion-matrix metric set."""
    true, pred = _validated_masks(y_true, y_prob, threshold)
    tp = int(np.logical_and(true, pred).sum())
    fp = int(np.logical_and(~true, pred).sum())
    fn = int(np.logical_and(true, ~pred).sum())
    tn = int(np.logical_and(~true, ~pred).sum())

    dice_denominator = 2 * tp + fp + fn
    union = tp + fp + fn
    return {
        "threshold": float(threshold),
        "hard_dice": float(2 * tp / dice_denominator) if dice_denominator else 1.0,
        "hard_iou": float(tp / union) if union else 1.0,
        "precision": float(tp / (tp + fp)) if tp + fp else float(true.sum() == 0),
        "recall": float(tp / (tp + fn)) if tp + fn else 1.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _boundary(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    structure = ndimage.generate_binary_structure(mask.ndim, 1)
    return mask ^ ndimage.binary_erosion(mask, structure=structure, border_value=0)


def boundary_segmentation_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    *,
    tolerance_pixels: float = 2.0,
    pixel_size: float | Sequence[float] = 1.0,
) -> dict[str, float]:
    """Compute Boundary F1, HD95 and ASSD from thresholded masks.

    If exactly one boundary is empty, distance metrics are infinite because
    there is no corresponding surface. Callers must not silently average that
    case into a finite score.
    """
    if tolerance_pixels < 0:
        raise ValueError("tolerance_pixels must be non-negative")
    true, pred = _validated_masks(y_true, y_prob, threshold)
    true_boundary = _boundary(true)
    pred_boundary = _boundary(pred)

    if not true_boundary.any() and not pred_boundary.any():
        return {"boundary_f1": 1.0, "hausdorff95": 0.0, "assd": 0.0}
    if not true_boundary.any() or not pred_boundary.any():
        return {"boundary_f1": 0.0, "hausdorff95": float("inf"), "assd": float("inf")}

    sampling = pixel_size
    distance_to_true = ndimage.distance_transform_edt(~true_boundary, sampling=sampling)
    distance_to_pred = ndimage.distance_transform_edt(~pred_boundary, sampling=sampling)
    pred_to_true = distance_to_true[pred_boundary]
    true_to_pred = distance_to_pred[true_boundary]

    if np.isscalar(pixel_size):
        tolerance = tolerance_pixels * float(pixel_size)
    else:
        tolerance = tolerance_pixels * float(max(pixel_size))
    precision = float(np.mean(pred_to_true <= tolerance))
    recall = float(np.mean(true_to_pred <= tolerance))
    boundary_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    distances = np.concatenate([pred_to_true, true_to_pred])
    return {
        "boundary_f1": float(boundary_f1),
        "hausdorff95": float(np.percentile(distances, 95)),
        "assd": float(distances.mean()),
    }


def area_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    *,
    pixel_area_m2: float,
) -> dict[str, float]:
    """Return signed/absolute glacier area errors in km² and percent."""
    if pixel_area_m2 <= 0:
        raise ValueError("pixel_area_m2 must be positive")
    true, pred = _validated_masks(y_true, y_prob, threshold)
    true_area = float(true.sum() * pixel_area_m2 / 1e6)
    predicted_area = float(pred.sum() * pixel_area_m2 / 1e6)
    error = predicted_area - true_area
    bias_percent = float(error / true_area * 100) if true_area else (0.0 if predicted_area == 0 else float("inf"))
    return {
        "true_area_km2": true_area,
        "predicted_area_km2": predicted_area,
        "area_error_km2": error,
        "absolute_area_error_km2": abs(error),
        "area_bias_percent": bias_percent,
        "area_error_percent": abs(bias_percent),
    }


def complete_segmentation_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.5,
    *,
    pixel_area_m2: float,
    pixel_size: float | Sequence[float] = 1.0,
    boundary_tolerance_pixels: float = 2.0,
) -> dict[str, float | int]:
    """Combine hard overlap, boundary and area metrics without soft/hard mixing."""
    return {
        **hard_segmentation_metrics(y_true, y_prob, threshold),
        **boundary_segmentation_metrics(
            y_true,
            y_prob,
            threshold,
            tolerance_pixels=boundary_tolerance_pixels,
            pixel_size=pixel_size,
        ),
        **area_metrics(y_true, y_prob, threshold, pixel_area_m2=pixel_area_m2),
    }


def calibrate_threshold(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    *,
    thresholds: Iterable[float] | None = None,
    pixel_area_m2: float,
) -> dict[str, Any]:
    """Select a threshold on validation data using a pre-declared objective.

    The objective is ``abs(area_bias_fraction) + (1 - hard_dice)``. Percent
    values are divided by 100 so both terms are dimensionless and comparable.
    Ties prefer the lower absolute area bias and then the lower threshold.
    """
    candidates = list(thresholds if thresholds is not None else np.round(np.arange(0.20, 0.801, 0.05), 2))
    if not candidates:
        raise ValueError("at least one threshold is required")
    rows: list[dict[str, float | int]] = []
    for threshold in candidates:
        row = {
            **hard_segmentation_metrics(y_true, y_prob, float(threshold)),
            **area_metrics(y_true, y_prob, float(threshold), pixel_area_m2=pixel_area_m2),
        }
        bias = float(row["area_bias_percent"])
        row["calibration_objective"] = abs(bias) / 100 + (1 - float(row["hard_dice"]))
        rows.append(row)
    best = min(
        rows,
        key=lambda row: (
            float(row["calibration_objective"]),
            abs(float(row["area_bias_percent"])),
            float(row["threshold"]),
        ),
    )
    return {
        "selection_split": "validation",
        "objective": "abs(area_bias_percent)/100 + (1-hard_dice)",
        "selected_threshold": float(best["threshold"]),
        "selected_metrics": best,
        "sweep": rows,
    }


def bootstrap_confidence_intervals(
    records: Sequence[Mapping[str, Any]],
    *,
    metrics: Sequence[str] = ("hard_dice", "hard_iou", "area_error_percent"),
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, dict[str, float | int]]:
    """Bootstrap glacier-level means, preserving the glacier as sample unit."""
    if not records:
        raise ValueError("records must not be empty")
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")
    missing = [metric for metric in metrics if any(metric not in record for record in records)]
    if missing:
        raise ValueError(f"missing bootstrap metrics: {sorted(set(missing))}")

    values = {metric: np.asarray([float(record[metric]) for record in records]) for metric in metrics}
    if any(not np.isfinite(array).all() for array in values.values()):
        raise ValueError("bootstrap inputs must be finite")
    rng = np.random.default_rng(seed)
    sample_indices = rng.integers(0, len(records), size=(n_resamples, len(records)))
    alpha = (1 - confidence) / 2
    output: dict[str, dict[str, float | int]] = {}
    for metric, array in values.items():
        distribution = array[sample_indices].mean(axis=1)
        output[metric] = {
            "estimate": float(array.mean()),
            "ci_lower": float(np.quantile(distribution, alpha)),
            "ci_upper": float(np.quantile(distribution, 1 - alpha)),
            "confidence": float(confidence),
            "n_glaciers": len(records),
            "n_resamples": n_resamples,
            "seed": seed,
        }
    return output


def bootstrap_paired_difference(
    records: Sequence[Mapping[str, Any]],
    *,
    baseline_key: str,
    candidate_key: str,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> dict[str, float | int | bool]:
    """Bootstrap a paired candidate-minus-baseline glacier-level difference."""
    if not records:
        raise ValueError("records must not be empty")
    differences = np.asarray(
        [float(record[candidate_key]) - float(record[baseline_key]) for record in records],
        dtype=np.float64,
    )
    if not np.isfinite(differences).all():
        raise ValueError("paired bootstrap inputs must be finite")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differences), size=(n_resamples, len(differences)))
    distribution = differences[indices].mean(axis=1)
    alpha = (1 - confidence) / 2
    lower = float(np.quantile(distribution, alpha))
    upper = float(np.quantile(distribution, 1 - alpha))
    return {
        "estimate": float(differences.mean()),
        "ci_lower": lower,
        "ci_upper": upper,
        "confidence": confidence,
        "n_glaciers": len(records),
        "n_resamples": n_resamples,
        "seed": seed,
        "statistically_confirmed": bool(lower > 0 or upper < 0),
    }
