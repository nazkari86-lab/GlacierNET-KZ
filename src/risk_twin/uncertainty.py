"""Calibration and uncertainty propagation without unsupported hazard claims."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np


def split_conformal_radius(
    calibration_residuals: Sequence[float],
    *,
    miscoverage: float = 0.1,
) -> float:
    """Return the finite-sample split-conformal absolute-residual radius."""
    if not 0 < miscoverage < 1:
        raise ValueError("miscoverage must be between zero and one")
    residuals = np.asarray(calibration_residuals, dtype=float)
    if residuals.ndim != 1 or residuals.size == 0:
        raise ValueError("calibration_residuals must be a non-empty one-dimensional sequence")
    if not np.all(np.isfinite(residuals)) or np.any(residuals < 0):
        raise ValueError("calibration residuals must be finite and non-negative")
    rank = min(residuals.size, math.ceil((residuals.size + 1) * (1 - miscoverage)))
    return float(np.partition(residuals, rank - 1)[rank - 1])


def split_conformal_interval(
    prediction: float,
    calibration_residuals: Sequence[float],
    *,
    miscoverage: float = 0.1,
    lower_bound: float | None = None,
) -> dict[str, Any]:
    """Create a symmetric split-conformal interval and retain its assumptions."""
    if not math.isfinite(prediction):
        raise ValueError("prediction must be finite")
    radius = split_conformal_radius(calibration_residuals, miscoverage=miscoverage)
    lower = prediction - radius
    if lower_bound is not None:
        if not math.isfinite(lower_bound):
            raise ValueError("lower_bound must be finite")
        lower = max(lower, lower_bound)
    return {
        "point": prediction,
        "lower": lower,
        "upper": prediction + radius,
        "radius": radius,
        "nominal_coverage": 1 - miscoverage,
        "calibration_size": len(calibration_residuals),
        "guarantee_scope": "marginal coverage under exchangeability; not per-basin hazard coverage",
    }


def propagate_uncertainty_chain(
    initial_samples: Sequence[float],
    stages: Sequence[tuple[str, Callable[[np.ndarray], np.ndarray]]],
    *,
    quantiles: tuple[float, float] = (0.05, 0.95),
) -> dict[str, Any]:
    """Propagate one ensemble through declared transforms and preserve every stage."""
    low, high = quantiles
    if not 0 <= low < high <= 1:
        raise ValueError("quantiles must satisfy 0 <= low < high <= 1")
    samples = np.asarray(initial_samples, dtype=float)
    if samples.ndim != 1 or samples.size < 2 or not np.all(np.isfinite(samples)):
        raise ValueError("initial_samples must contain at least two finite values")
    records: list[dict[str, Any]] = []
    for name, transform in stages:
        if not name.strip():
            raise ValueError("uncertainty stage name is required")
        transformed = np.asarray(transform(samples), dtype=float)
        if transformed.shape != samples.shape:
            raise ValueError(f"stage {name} must preserve ensemble shape")
        if not np.all(np.isfinite(transformed)):
            raise ValueError(f"stage {name} produced non-finite values")
        samples = transformed
        records.append(
            {
                "stage": name,
                "mean": float(np.mean(samples)),
                "std": float(np.std(samples, ddof=1)),
                "interval": [
                    float(np.quantile(samples, low)),
                    float(np.quantile(samples, high)),
                ],
                "sample_count": int(samples.size),
            }
        )
    return {
        "quantiles": [low, high],
        "stages": records,
        "final_samples": samples.tolist(),
        "interpretation": "declared ensemble propagation; validity depends on input ensemble and stage models",
    }


def sensitivity_summary(
    baseline: Sequence[float],
    scenarios: Mapping[str, Sequence[float]],
) -> list[dict[str, Any]]:
    """Compare scenario ensembles without promoting them to interventions."""
    reference = np.asarray(baseline, dtype=float)
    if reference.ndim != 1 or reference.size < 2 or not np.all(np.isfinite(reference)):
        raise ValueError("baseline must contain at least two finite values")
    rows = []
    for name, values in scenarios.items():
        scenario = np.asarray(values, dtype=float)
        if scenario.shape != reference.shape or not np.all(np.isfinite(scenario)):
            raise ValueError(f"scenario {name} must match the finite baseline ensemble")
        delta = scenario - reference
        rows.append(
            {
                "scenario": name,
                "mean_delta": float(np.mean(delta)),
                "median_delta": float(np.median(delta)),
                "probability_delta_below_zero": float(np.mean(delta < 0)),
                "engineering_recommendation": False,
            }
        )
    return rows
