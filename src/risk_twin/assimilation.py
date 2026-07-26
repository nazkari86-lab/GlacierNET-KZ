"""Transparent scalar Kalman-filter baseline for partial basin observations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from .schemas import BasinState, GaussianEstimate, Observation, StateVariable

DEFAULT_PROCESS_VARIANCE_PER_DAY: dict[StateVariable, float] = {
    StateVariable.GLACIER_AREA: 1_000.0,
    StateVariable.GLACIER_VELOCITY: 0.25,
    StateVariable.LAKE_AREA: 2_500.0,
    StateVariable.WATER_LEVEL: 0.01,
    StateVariable.FREEBOARD: 0.01,
    StateVariable.DAM_STABILITY: 0.0025,
    StateVariable.OUTLET_CAPACITY: 0.0025,
    StateVariable.SLOPE_DEFORMATION: 0.25,
    StateVariable.METEO_FORCING: 0.01,
    StateVariable.CHANNEL_CAPACITY: 1.0,
    StateVariable.EXPOSURE: 0.01,
}


def _elapsed_days(earlier: datetime, later: datetime) -> float:
    left = earlier.timestamp()
    right = later.timestamp()
    if right < left:
        raise ValueError("observations must not move basin state backwards in time")
    return (right - left) / 86400


def assimilate_observation(
    state: BasinState,
    observation: Observation,
    *,
    process_variance_per_day: Mapping[StateVariable, float] | None = None,
) -> BasinState:
    """Update one state variable and retain auditable Kalman diagnostics."""
    if observation.basin_id != state.basin_id:
        raise ValueError("observation basin_id does not match state")
    elapsed_days = _elapsed_days(state.timestamp, observation.timestamp)
    process = process_variance_per_day or DEFAULT_PROCESS_VARIANCE_PER_DAY
    measurement_variance = observation.uncertainty_std**2
    previous = state.estimates.get(observation.variable)

    if previous is None:
        posterior = GaussianEstimate(
            mean=observation.value,
            variance=measurement_variance,
            updated_at=observation.timestamp,
            observation_count=1,
            source_ids=[observation.observation_id],
        )
        prior_variance = None
        kalman_gain = 1.0
    else:
        prior_variance = previous.variance + elapsed_days * float(process.get(observation.variable, 0.0))
        kalman_gain = prior_variance / (prior_variance + measurement_variance)
        posterior = GaussianEstimate(
            mean=previous.mean + kalman_gain * (observation.value - previous.mean),
            variance=(1 - kalman_gain) * prior_variance,
            updated_at=observation.timestamp,
            observation_count=previous.observation_count + 1,
            source_ids=[*previous.source_ids, observation.observation_id],
        )

    state.estimates[observation.variable] = posterior
    state.timestamp = observation.timestamp
    state.provenance.append(
        {
            "operation": "scalar_kalman_update",
            "observation": observation.to_dict(),
            "prior_variance": prior_variance,
            "measurement_variance": measurement_variance,
            "kalman_gain": kalman_gain,
            "posterior": posterior.to_dict(),
        }
    )
    return state


def assimilate_many(
    basin_id: str,
    observations: Iterable[Observation],
    *,
    initial_timestamp: datetime | None = None,
) -> BasinState:
    ordered = sorted(observations, key=lambda item: item.timestamp)
    if not ordered and initial_timestamp is None:
        raise ValueError("at least one observation or initial_timestamp is required")
    timestamp = initial_timestamp or ordered[0].timestamp
    identifiers = [item.observation_id for item in ordered]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("observation_id values must be unique within an assimilation run")
    state = BasinState(basin_id=basin_id, timestamp=timestamp)
    for observation in ordered:
        assimilate_observation(state, observation)
    return state
