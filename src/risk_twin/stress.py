"""Transparent virtual stress testing over explicitly declared scenario models."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StressScenario:
    scenario_id: str
    stresses: dict[str, float]
    physical_cost: float
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip() or not self.stresses:
            raise ValueError("scenario_id and at least one stress variable are required")
        if not math.isfinite(self.physical_cost) or self.physical_cost < 0:
            raise ValueError("physical_cost must be finite and non-negative")
        if any(not key.strip() for key in self.stresses):
            raise ValueError("stress variable names must be non-empty")
        if any(not math.isfinite(value) or value < 0 for value in self.stresses.values()):
            raise ValueError("stress values must be finite and non-negative")


@dataclass(frozen=True)
class LinearStressModel:
    """Auditable baseline; coefficients require external calibration."""

    coefficients: dict[str, float]
    intercept: float
    transition_threshold: float
    state_coefficients: dict[str, float] = field(default_factory=dict)
    calibrated: bool = False
    calibration_reference: str | None = None
    model_id: str = "linear_stress_screen_v1"
    variable_units: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = [
            self.intercept,
            self.transition_threshold,
            *self.coefficients.values(),
            *self.state_coefficients.values(),
        ]
        if not self.coefficients or any(not math.isfinite(value) for value in values):
            raise ValueError("stress model coefficients, intercept and threshold must be finite")
        if self.calibrated and not self.calibration_reference:
            raise ValueError("calibration_reference is required when calibrated=True")

    def evaluate(self, scenario: StressScenario, *, state_features: dict[str, float]) -> dict[str, Any]:
        unknown = sorted(set(scenario.stresses) - set(self.coefficients))
        missing = sorted(set(self.coefficients) - set(scenario.stresses))
        missing_state = sorted(set(self.state_coefficients) - set(state_features))
        if missing_state:
            raise ValueError("stress model requires missing state features: " + ", ".join(missing_state))
        if any(not math.isfinite(value) for value in state_features.values()):
            raise ValueError("state features must be finite")
        stress_contribution = sum(
            coefficient * scenario.stresses.get(variable, 0.0) for variable, coefficient in self.coefficients.items()
        )
        state_contribution = sum(
            coefficient * state_features[variable] for variable, coefficient in self.state_coefficients.items()
        )
        score = self.intercept + stress_contribution + state_contribution
        exceeded = score >= self.transition_threshold
        return {
            "scenario_id": scenario.scenario_id,
            "stresses": dict(scenario.stresses),
            "physical_cost": scenario.physical_cost,
            "model_score": score,
            "stress_contribution": stress_contribution,
            "state_contribution": state_contribution,
            "model_threshold": self.transition_threshold,
            "model_threshold_exceeded": exceeded,
            "transition_status": "threshold_exceeded" if exceeded else "threshold_not_exceeded",
            "unknown_stress_variables": unknown,
            "model_variables_not_stressed": missing,
            "provenance": list(scenario.provenance),
        }


def run_stress_surface(
    model: LinearStressModel,
    scenarios: list[StressScenario],
    *,
    state_features: dict[str, float],
) -> dict[str, Any]:
    if not scenarios:
        raise ValueError("at least one stress scenario is required")
    if len({scenario.scenario_id for scenario in scenarios}) != len(scenarios):
        raise ValueError("scenario_id values must be unique")
    results = [model.evaluate(scenario, state_features=state_features) for scenario in scenarios]
    exceeded = [result for result in results if result["model_threshold_exceeded"]]
    minimum = min(exceeded, key=lambda result: (result["physical_cost"], result["scenario_id"])) if exceeded else None
    return {
        "model_id": model.model_id,
        "model_type": "transparent_linear_screen",
        "model_calibrated": model.calibrated,
        "calibration_reference": model.calibration_reference,
        "variable_units": dict(model.variable_units),
        "state_features": dict(state_features),
        "state_coefficients": dict(model.state_coefficients),
        "scenarios": results,
        "resilience_margin": {
            "value": minimum["physical_cost"] if minimum else None,
            "units": "declared_normalized_physical_cost",
            "critical_scenario_id": minimum["scenario_id"] if minimum else None,
            "right_censored": minimum is None,
            "class": (
                "external_calibration_required"
                if not model.calibrated
                else ("within_tested_surface" if minimum else "above_tested_surface")
            ),
        },
        "claim_status": "calibrated_model_screening" if model.calibrated else "unvalidated_model_screening",
        "safety_statement": (
            "Threshold crossing is a model stress-test result, not an event probability or official warning."
        ),
    }
