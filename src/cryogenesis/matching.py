"""Deterministic, leakage-safe counterfactual glacier matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import cast

import numpy as np

from .cohort import validate_pre_outcome_features
from .schemas import (
    FeatureValue,
    GlacierFeatureRecord,
    MatchResult,
    MatchStatus,
    TwinMatch,
)


@dataclass(frozen=True)
class MatchConfig:
    """Frozen matching policy declared before outcome evaluation."""

    feature_weights: dict[str, float]
    hard_calipers: dict[str, float] = field(default_factory=dict)
    maximum_distance: float = 3.0
    maximum_twins: int = 5
    minimum_primary_twins: int = 3
    scale_floor: float = 1e-9

    def __post_init__(self) -> None:
        if not self.feature_weights:
            raise ValueError("feature_weights must not be empty")
        if any(weight <= 0 for weight in self.feature_weights.values()):
            raise ValueError("feature weights must be positive")
        if any(caliper < 0 for caliper in self.hard_calipers.values()):
            raise ValueError("hard calipers must be non-negative")
        if self.maximum_distance < 0:
            raise ValueError("maximum_distance must be non-negative")
        if self.maximum_twins < 1:
            raise ValueError("maximum_twins must be at least one")
        if self.minimum_primary_twins < 1:
            raise ValueError("minimum_primary_twins must be at least one")
        if self.scale_floor <= 0:
            raise ValueError("scale_floor must be positive")


def _is_aspect(feature_name: str) -> bool:
    normalized = feature_name.lower()
    return normalized in {"aspect", "aspect_deg", "aspect_degrees"} or (normalized.endswith("_aspect_deg"))


def _numeric_value(feature: FeatureValue | None) -> float | None:
    if feature is None or feature.quality_state != "observed":
        return None
    if not isinstance(feature.value, (int, float)):
        return None
    value = float(feature.value)
    return value if isfinite(value) else None


def _raw_difference(
    feature_name: str,
    target_value: float,
    candidate_value: float,
) -> float:
    difference = abs(target_value - candidate_value)
    if _is_aspect(feature_name):
        wrapped = difference % 360.0
        return min(wrapped, 360.0 - wrapped)
    return difference


def _development_scales(
    records: list[GlacierFeatureRecord],
    required_features: tuple[str, ...],
    floor: float,
) -> dict[str, float]:
    development = [record for record in records if record.split == "development"]
    scale_population = development or records
    scales: dict[str, float] = {}

    for feature_name in required_features:
        if _is_aspect(feature_name):
            scales[feature_name] = 180.0
            continue
        values = [
            value
            for record in scale_population
            if (value := _numeric_value(record.features.get(feature_name))) is not None
        ]
        if len(values) < 2:
            scales[feature_name] = floor
            continue
        lower, upper = np.percentile(values, [25, 75])
        scales[feature_name] = max(float(upper - lower), floor)

    return scales


def match_twins(
    target: GlacierFeatureRecord,
    cohort: list[GlacierFeatureRecord],
    config: MatchConfig,
) -> MatchResult:
    """Select an auditable comparator set without consulting outcome values."""

    required_features = tuple(sorted(config.feature_weights))
    validate_pre_outcome_features(target, required_features)
    scales = _development_scales(cohort, required_features, config.scale_floor)
    target_values = {
        feature_name: _numeric_value(target.features.get(feature_name)) for feature_name in required_features
    }
    if any(value is None for value in target_values.values()):
        missing = [name for name, value in target_values.items() if value is None]
        raise ValueError("target has non-numeric or unobserved required features: " + ", ".join(missing))

    accepted: list[tuple[float, str, dict[str, float]]] = []
    rejected: dict[str, str] = {}
    weight_sum = float(sum(config.feature_weights.values()))

    for candidate in cohort:
        if candidate.rgi_id == target.rgi_id:
            rejected[candidate.rgi_id] = "self_match_forbidden"
            continue
        if candidate.split != target.split:
            rejected[candidate.rgi_id] = "frozen_split_boundary"
            continue
        if candidate.anchor_year != target.anchor_year:
            rejected[candidate.rgi_id] = "anchor_year_mismatch"
            continue
        if candidate.outcome_year != target.outcome_year:
            rejected[candidate.rgi_id] = "outcome_year_mismatch"
            continue
        if candidate.outcome is None:
            rejected[candidate.rgi_id] = "missing_outcome"
            continue

        try:
            validate_pre_outcome_features(candidate, required_features)
        except ValueError as error:
            rejected[candidate.rgi_id] = str(error)
            continue

        candidate_values = {
            feature_name: _numeric_value(candidate.features.get(feature_name)) for feature_name in required_features
        }
        missing = [name for name, value in candidate_values.items() if value is None]
        if missing:
            rejected[candidate.rgi_id] = "non-numeric or unobserved required features: " + ", ".join(missing)
            continue

        component_distances: dict[str, float] = {}
        failed_caliper: str | None = None
        for feature_name in required_features:
            target_value = cast(float, target_values[feature_name])
            candidate_value = cast(float, candidate_values[feature_name])
            raw_difference = _raw_difference(feature_name, target_value, candidate_value)
            caliper = config.hard_calipers.get(feature_name)
            if caliper is not None and raw_difference > caliper:
                failed_caliper = feature_name
                break
            component_distances[feature_name] = raw_difference / scales[feature_name]

        if failed_caliper is not None:
            rejected[candidate.rgi_id] = f"hard_caliper_exceeded:{failed_caliper}"
            continue

        total_distance = (
            sum(config.feature_weights[name] * component_distances[name] for name in required_features) / weight_sum
        )
        if total_distance > config.maximum_distance:
            rejected[candidate.rgi_id] = "maximum_distance_exceeded"
            continue
        accepted.append((float(total_distance), candidate.rgi_id, component_distances))

    accepted.sort(key=lambda item: (item[0], item[1]))
    selected = accepted[: config.maximum_twins]
    if not selected:
        status: MatchStatus = "no_valid_counterfactual"
        return MatchResult(target.rgi_id, status, (), rejected)

    inverse_distances = [1.0 / max(distance, config.scale_floor) for distance, _, _ in selected]
    inverse_sum = sum(inverse_distances)
    twins = tuple(
        TwinMatch(
            rgi_id=rgi_id,
            total_distance=distance,
            component_distances=components,
            weight=inverse_distance / inverse_sum,
        )
        for (distance, rgi_id, components), inverse_distance in zip(selected, inverse_distances)
    )
    status = cast(
        MatchStatus,
        "matched" if len(twins) >= config.minimum_primary_twins else "limited_match",
    )
    return MatchResult(target.rgi_id, status, twins, rejected)
