"""Bounded retrospective outcome divergence for matched glacier sets."""

from __future__ import annotations

from math import isclose, isfinite

import numpy as np

from .schemas import DivergenceResult


def _weighted_mean(values: tuple[float, ...], weights: tuple[float, ...]) -> float:
    return float(sum(value * weight for value, weight in zip(values, weights)))


def estimate_divergence(
    target_outcome: float,
    twin_outcomes: tuple[float, ...],
    weights: tuple[float, ...],
) -> DivergenceResult:
    """Compare a target outcome with its fixed weighted comparator set."""

    if not twin_outcomes or len(twin_outcomes) != len(weights):
        raise ValueError("twin outcomes and weights must have equal non-zero length")
    values = (target_outcome, *twin_outcomes, *weights)
    if not all(isfinite(value) for value in values):
        raise ValueError("outcomes and weights must be finite")
    if any(weight < 0 for weight in weights):
        raise ValueError("weights must be non-negative")
    if not isclose(sum(weights), 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("weights must be normalised to one")

    comparator = _weighted_mean(twin_outcomes, weights)
    raw_divergence = float(target_outcome - comparator)
    spread = float(np.std(twin_outcomes))
    standardized = None if spread == 0 else raw_divergence / spread

    leave_one_out: list[float] = []
    for excluded_index in range(len(twin_outcomes)):
        retained = [
            (outcome, weight)
            for index, (outcome, weight) in enumerate(
                zip(twin_outcomes, weights)
            )
            if index != excluded_index
        ]
        retained_weight = sum(weight for _, weight in retained)
        if retained and retained_weight > 0:
            leave_one_out.append(
                sum(outcome * weight for outcome, weight in retained)
                / retained_weight
            )
    if not leave_one_out:
        leave_one_out = [comparator]

    return DivergenceResult(
        target_outcome=float(target_outcome),
        comparator_outcome=comparator,
        raw_divergence=raw_divergence,
        standardized_divergence=standardized,
        comparator_interval=(min(twin_outcomes), max(twin_outcomes)),
        leave_one_out_range=(min(leave_one_out), max(leave_one_out)),
    )

