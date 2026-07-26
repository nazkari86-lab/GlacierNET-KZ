"""Typed observations and latent basin state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any


class StateVariable(str, Enum):
    GLACIER_AREA = "glacier_area_m2"
    GLACIER_VELOCITY = "glacier_velocity_m_per_year"
    LAKE_AREA = "lake_area_m2"
    WATER_LEVEL = "water_level_m"
    FREEBOARD = "freeboard_m"
    DAM_STABILITY = "dam_stability_index"
    OUTLET_CAPACITY = "outlet_capacity_fraction"
    SLOPE_DEFORMATION = "slope_deformation_mm_per_year"
    METEO_FORCING = "meteo_forcing_index"
    CHANNEL_CAPACITY = "channel_capacity_m3_s"
    EXPOSURE = "exposed_asset_count"


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class Observation:
    observation_id: str
    basin_id: str
    variable: StateVariable
    value: float
    uncertainty_std: float
    timestamp: datetime
    sensor: str
    quality_flags: tuple[str, ...] = ()
    spatial_support: str = "basin_screening"

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.basin_id.strip() or not self.sensor.strip():
            raise ValueError("observation_id, basin_id and sensor are required")
        if self.uncertainty_std <= 0:
            raise ValueError("uncertainty_std must be positive")
        if not isfinite(self.value) or not isfinite(self.uncertainty_std):
            raise ValueError("observation value and uncertainty_std must be finite")
        if not self.spatial_support.strip():
            raise ValueError("spatial_support is required")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["variable"] = self.variable.value
        payload["timestamp"] = _utc_iso(self.timestamp)
        payload["quality_flags"] = list(self.quality_flags)
        return payload


@dataclass
class GaussianEstimate:
    mean: float
    variance: float
    updated_at: datetime
    observation_count: int = 1
    source_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isfinite(self.mean) or not isfinite(self.variance) or self.variance <= 0:
            raise ValueError("estimate mean must be finite and variance must be finite and positive")
        if self.observation_count < 0:
            raise ValueError("observation_count must be non-negative")

    @property
    def std(self) -> float:
        return self.variance**0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean": self.mean,
            "variance": self.variance,
            "std": self.std,
            "ci95": [self.mean - 1.96 * self.std, self.mean + 1.96 * self.std],
            "updated_at": _utc_iso(self.updated_at),
            "observation_count": self.observation_count,
            "source_ids": list(self.source_ids),
        }


@dataclass
class BasinState:
    basin_id: str
    timestamp: datetime
    estimates: dict[StateVariable, GaussianEstimate] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    probability_calibrated: bool = False
    calibration_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.basin_id.strip():
            raise ValueError("basin_id is required")
        if self.probability_calibrated and not self.calibration_reference:
            raise ValueError("calibration_reference is required for calibrated state")

    def data_gaps(self, required: set[StateVariable] | None = None) -> list[str]:
        expected = required or set(StateVariable)
        return sorted(variable.value for variable in expected - set(self.estimates))

    def to_dict(self) -> dict[str, Any]:
        return {
            "basin_id": self.basin_id,
            "timestamp": _utc_iso(self.timestamp),
            "state": {variable.value: estimate.to_dict() for variable, estimate in self.estimates.items()},
            "data_gaps": self.data_gaps(),
            "probability_calibrated": self.probability_calibrated,
            "calibration_reference": self.calibration_reference,
            "provenance": list(self.provenance),
        }
