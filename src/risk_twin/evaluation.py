"""Decision-focused retrospective evaluation metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from statistics import median
from typing import Any

import numpy as np

from .schemas import Observation


def ranking_metrics(
    ranked_ids: Sequence[str], relevant_ids: set[str], *, ks: Sequence[int] = (5, 10)
) -> dict[str, float]:
    if not relevant_ids:
        raise ValueError("relevant_ids must not be empty")
    output = {}
    for k in ks:
        if k <= 0:
            raise ValueError("ranking cutoffs must be positive")
        output[f"recall_at_{k}"] = len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)
    reciprocal_ranks = [1 / (index + 1) for index, item in enumerate(ranked_ids) if item in relevant_ids]
    output["mean_reciprocal_rank"] = max(reciprocal_ranks, default=0.0)
    return output


def warning_metrics(
    event_times: dict[str, datetime],
    warnings: Iterable[tuple[str, datetime]],
    *,
    observation_years: float,
) -> dict[str, Any]:
    warning_list = list(warnings)
    lead_times = []
    true_event_ids = set()
    false_alerts = 0
    for basin_id, warning_time in warning_list:
        event_time = event_times.get(basin_id)
        if event_time is not None and warning_time <= event_time:
            lead_times.append((event_time - warning_time).total_seconds() / 86400)
            true_event_ids.add(basin_id)
        else:
            false_alerts += 1
    missed = len(set(event_times) - true_event_ids)
    return {
        "median_lead_time_days": float(median(lead_times)) if lead_times else None,
        "false_alerts_per_basin_year": false_alerts / observation_years if observation_years > 0 else None,
        "missed_events": missed,
        "detected_events": len(true_event_ids),
    }


def decision_regret(selected_utility: float, oracle_utilities: Sequence[float]) -> float:
    if not oracle_utilities:
        raise ValueError("oracle_utilities must not be empty")
    return max(oracle_utilities) - selected_utility


def gaussian_crps(mean: float, std: float, observed: float) -> float:
    """Closed-form CRPS for a Gaussian forecast."""
    if std <= 0:
        raise ValueError("std must be positive")
    z = (observed - mean) / std
    normal_pdf = math.exp(-(z**2) / 2) / math.sqrt(2 * math.pi)
    normal_cdf = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return std * (z * (2 * normal_cdf - 1) + 2 * normal_pdf - 1 / math.sqrt(math.pi))


def interval_coverage(intervals: Sequence[tuple[float, float]], observations: Sequence[float]) -> float:
    if len(intervals) != len(observations) or not intervals:
        raise ValueError("intervals and observations must have equal non-zero length")
    return float(np.mean([lower <= observed <= upper for (lower, upper), observed in zip(intervals, observations)]))


def truncate_for_event_replay(
    observations: Iterable[Observation],
    *,
    event_time: datetime,
    lead_time_days: int = 90,
) -> tuple[list[Observation], dict[str, Any]]:
    """Hide observations newer than T-minus-lead-time and report leakage audit."""
    if lead_time_days < 0:
        raise ValueError("lead_time_days must be non-negative")
    cutoff = event_time - timedelta(days=lead_time_days)
    all_observations = sorted(observations, key=lambda item: item.timestamp)
    allowed = [observation for observation in all_observations if observation.timestamp <= cutoff]
    hidden = [observation for observation in all_observations if observation.timestamp > cutoff]
    return allowed, {
        "event_time": event_time.isoformat(),
        "cutoff_time": cutoff.isoformat(),
        "lead_time_days": lead_time_days,
        "allowed_observations": len(allowed),
        "hidden_observations": len(hidden),
        "post_cutoff_observation_ids": [observation.observation_id for observation in hidden],
        "leakage_detected": any(observation.timestamp > cutoff for observation in allowed),
    }
