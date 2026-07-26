"""Resilience diagnostics with explicit sampling and interpretation limits."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any

import numpy as np


def _series(timestamps: Sequence[datetime], values: Sequence[float]) -> tuple[list[datetime], np.ndarray]:
    if len(timestamps) != len(values) or len(values) < 3:
        raise ValueError("timestamps and values must have equal length of at least three")
    if any(left >= right for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("timestamps must be strictly increasing")
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError("time-series values must be finite")
    return list(timestamps), array


def monthly_climatology_residuals(
    timestamps: Sequence[datetime],
    values: Sequence[float],
    *,
    min_samples_per_month: int = 2,
) -> dict[str, Any]:
    """Remove a monthly climatology while exposing unsupported months."""
    ordered, array = _series(timestamps, values)
    if min_samples_per_month < 2:
        raise ValueError("min_samples_per_month must be at least two")
    groups: dict[int, list[float]] = defaultdict(list)
    for timestamp, value in zip(ordered, array):
        groups[timestamp.month].append(float(value))
    unsupported = sorted(month for month, group in groups.items() if len(group) < min_samples_per_month)
    climatology = {
        month: float(np.mean(group)) for month, group in groups.items() if len(group) >= min_samples_per_month
    }
    residuals = [
        float(value - climatology[timestamp.month]) if timestamp.month in climatology else None
        for timestamp, value in zip(ordered, array)
    ]
    return {
        "residuals": residuals,
        "monthly_climatology": climatology,
        "unsupported_months": unsupported,
        "ready": not unsupported,
        "interpretation": "monthly mean removal; not proof that all seasonality was removed",
    }


def lag1_diagnostic(
    values: Sequence[float],
    *,
    timestamps: Sequence[datetime] | None = None,
    max_gap_ratio: float = 2.0,
) -> dict[str, Any]:
    """Calculate lag-1 correlation and audit irregular temporal gaps."""
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size < 4 or not np.all(np.isfinite(array)):
        raise ValueError("values must contain at least four finite observations")
    if max_gap_ratio < 1:
        raise ValueError("max_gap_ratio must be at least one")
    gap_audit = None
    if timestamps is not None:
        if len(timestamps) != array.size or any(left >= right for left, right in zip(timestamps, timestamps[1:])):
            raise ValueError("timestamps must match values and be strictly increasing")
        gaps = np.diff([timestamp.timestamp() for timestamp in timestamps])
        median_gap = float(np.median(gaps))
        gap_audit = {
            "median_gap_days": median_gap / 86400,
            "maximum_gap_days": float(np.max(gaps)) / 86400,
            "irregular": bool(np.max(gaps) > max_gap_ratio * median_gap),
            "max_gap_ratio": max_gap_ratio,
        }
    left = array[:-1]
    right = array[1:]
    if np.std(left) == 0 or np.std(right) == 0:
        correlation = None
    else:
        correlation = float(np.corrcoef(left, right)[0, 1])
    return {
        "lag1_autocorrelation": correlation,
        "variance": float(np.var(array, ddof=1)),
        "sample_count": int(array.size),
        "gap_audit": gap_audit,
        "claim_status": "diagnostic_only",
        "interpretation": "cannot independently establish critical slowing down or forecast a GLOF",
    }


def response_gain(forcing: Sequence[float], response: Sequence[float]) -> dict[str, Any]:
    """Fit a transparent one-predictor response slope with diagnostics."""
    x = np.asarray(forcing, dtype=float)
    y = np.asarray(response, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or x.size < 4:
        raise ValueError("forcing and response must have equal one-dimensional length of at least four")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)) or np.var(x) == 0:
        raise ValueError("forcing and response must be finite and forcing must vary")
    design = np.column_stack([np.ones(x.size), x])
    intercept, gain = np.linalg.lstsq(design, y, rcond=None)[0]
    fitted = intercept + gain * x
    residual_sum = float(np.sum((y - fitted) ** 2))
    total_sum = float(np.sum((y - np.mean(y)) ** 2))
    return {
        "intercept": float(intercept),
        "response_gain": float(gain),
        "r_squared": 1 - residual_sum / total_sum if total_sum > 0 else None,
        "sample_count": int(x.size),
        "claim_status": "association_not_causation",
    }


def recovery_times(
    timestamps: Sequence[datetime],
    values: Sequence[float],
    event_indices: Sequence[int],
    *,
    baseline_points: int = 3,
    tolerance_std: float = 1.0,
) -> dict[str, Any]:
    """Measure observed return time after declared natural perturbations."""
    ordered, array = _series(timestamps, values)
    if baseline_points < 2 or tolerance_std <= 0:
        raise ValueError("baseline_points must be at least two and tolerance_std must be positive")
    records = []
    for index in event_indices:
        if index < baseline_points or index >= len(array) - 1:
            raise ValueError("each event index needs baseline and post-event observations")
        baseline = array[index - baseline_points : index]
        center = float(np.mean(baseline))
        spread = float(np.std(baseline, ddof=1))
        tolerance = max(tolerance_std * spread, np.finfo(float).eps)
        recovery_index = next(
            (candidate for candidate in range(index + 1, len(array)) if abs(array[candidate] - center) <= tolerance),
            None,
        )
        records.append(
            {
                "event_index": index,
                "event_time": ordered[index].isoformat(),
                "baseline_mean": center,
                "baseline_std": spread,
                "recovered": recovery_index is not None,
                "recovery_time_days": (
                    (ordered[recovery_index] - ordered[index]).total_seconds() / 86400
                    if recovery_index is not None
                    else None
                ),
                "right_censored_at_days": (
                    None if recovery_index is not None else (ordered[-1] - ordered[index]).total_seconds() / 86400
                ),
            }
        )
    observed = [record["recovery_time_days"] for record in records if record["recovery_time_days"] is not None]
    return {
        "events": records,
        "median_observed_recovery_days": float(np.median(observed)) if observed else None,
        "censored_events": sum(not record["recovered"] for record in records),
        "claim_status": "observed_response_diagnostic",
    }


def local_stability(matrix: Sequence[Sequence[float]], *, model_calibrated: bool = False) -> dict[str, Any]:
    """Report the spectral radius of a declared discrete-time local model."""
    jacobian = np.asarray(matrix, dtype=float)
    if jacobian.ndim != 2 or jacobian.shape[0] != jacobian.shape[1] or jacobian.size == 0:
        raise ValueError("matrix must be a non-empty square matrix")
    if not np.all(np.isfinite(jacobian)):
        raise ValueError("matrix must be finite")
    eigenvalues = np.linalg.eigvals(jacobian)
    radius = float(np.max(np.abs(eigenvalues)))
    if radius < 0.8:
        regime = "perturbations_decay_in_declared_local_model"
    elif radius < 1:
        regime = "slow_decay_in_declared_local_model"
    else:
        regime = "perturbations_can_amplify_in_declared_local_model"
    return {
        "spectral_radius": radius,
        "regime": regime,
        "eigenvalues": [{"real": float(value.real), "imag": float(value.imag)} for value in eigenvalues],
        "model_calibrated": model_calibrated,
        "claim_status": "model_diagnostic" if model_calibrated else "unvalidated_model_diagnostic",
        "safety_statement": "spectral radius alone does not predict a GLOF",
    }
