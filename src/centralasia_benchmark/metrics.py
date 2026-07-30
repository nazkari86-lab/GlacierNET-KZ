"""Metrics unique to the CentralAsia-GlacierBench evidence tracks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def temporal_stability_metrics(
    areas: Sequence[float],
    *,
    max_annual_change_fraction: float = 0.35,
) -> dict[str, float | int]:
    """Quantify annual jumps without assuming retreat must be monotonic."""
    values = np.asarray(areas, dtype=np.float64)
    if values.size < 2 or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("at least two finite, non-negative areas are required")
    denominator = np.maximum(values[:-1], 1e-9)
    relative_change = np.diff(values) / denominator
    implausible = np.abs(relative_change) > max_annual_change_fraction
    return {
        "n_observations": int(values.size),
        "median_absolute_annual_change_fraction": float(np.median(np.abs(relative_change))),
        "max_absolute_annual_change_fraction": float(np.max(np.abs(relative_change))),
        "implausible_jump_count": int(implausible.sum()),
        "stability_fraction": float(1.0 - implausible.mean()),
    }


def physical_consistency_metrics(
    *,
    glacier_probability: np.ndarray,
    dhdt: np.ndarray | None = None,
    velocity: np.ndarray | None = None,
    min_velocity_m_per_year: float = 1.0,
) -> dict[str, float | int | str | None]:
    """Evaluate independent physical support inside a predicted glacier mask.

    Missing physical layers are explicit. They never become neutral or positive
    evidence.
    """
    probability = np.asarray(glacier_probability, dtype=np.float64)
    if probability.size == 0 or not np.isfinite(probability).all():
        raise ValueError("glacier_probability must contain finite values")
    mask = probability >= 0.5
    if not mask.any():
        return {
            "status": "empty_prediction",
            "predicted_pixels": 0,
            "thinning_support_fraction": None,
            "motion_support_fraction": None,
            "available_evidence_count": 0,
        }
    output: dict[str, float | int | str | None] = {
        "status": "evaluated",
        "predicted_pixels": int(mask.sum()),
        "thinning_support_fraction": None,
        "motion_support_fraction": None,
        "available_evidence_count": 0,
    }
    if dhdt is not None:
        elevation_change = np.asarray(dhdt, dtype=np.float64)
        if elevation_change.shape != probability.shape:
            raise ValueError("dhdt shape must match glacier_probability")
        valid = mask & np.isfinite(elevation_change)
        if valid.any():
            output["thinning_support_fraction"] = float(np.mean(elevation_change[valid] < 0))
            output["available_evidence_count"] = int(output["available_evidence_count"]) + 1
    if velocity is not None:
        speed = np.asarray(velocity, dtype=np.float64)
        if speed.shape != probability.shape:
            raise ValueError("velocity shape must match glacier_probability")
        valid = mask & np.isfinite(speed)
        if valid.any():
            output["motion_support_fraction"] = float(np.mean(speed[valid] >= min_velocity_m_per_year))
            output["available_evidence_count"] = int(output["available_evidence_count"]) + 1
    if output["available_evidence_count"] == 0:
        output["status"] = "blocked_missing_physical_layers"
    return output


def event_control_metrics(records: Sequence[Mapping[str, Any]], *, score_key: str = "score") -> dict[str, Any]:
    """Evaluate a continuous cascade score against observed event/control labels."""
    if not records:
        raise ValueError("records must not be empty")
    scores = np.asarray([float(record[score_key]) for record in records], dtype=np.float64)
    labels = np.asarray([int(record["event"]) for record in records], dtype=np.int8)
    if not np.isfinite(scores).all() or not np.isin(labels, [0, 1]).all():
        raise ValueError("scores must be finite and event labels binary")
    if len(np.unique(labels)) < 2:
        return {
            "status": "blocked_single_class",
            "n_records": len(records),
            "n_events": int(labels.sum()),
            "n_controls": int((1 - labels).sum()),
            "roc_auc": None,
        }
    positive = scores[labels == 1]
    negative = scores[labels == 0]
    comparisons = positive[:, None] - negative[None, :]
    auc = float(np.mean(comparisons > 0) + 0.5 * np.mean(comparisons == 0))
    return {
        "status": "evaluated",
        "n_records": len(records),
        "n_events": int(labels.sum()),
        "n_controls": int((1 - labels).sum()),
        "roc_auc": auc,
        "mean_event_score": float(positive.mean()),
        "mean_control_score": float(negative.mean()),
    }
