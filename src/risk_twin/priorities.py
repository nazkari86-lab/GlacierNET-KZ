"""Separate potential-hazard and evidence-acquisition priorities."""

from __future__ import annotations

from typing import Any


def _unit(value: float, name: str) -> float:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between zero and one")
    return float(value)


def priority_pair(
    *,
    current_anomaly: float,
    resilience_vulnerability: float | None,
    potential_consequence: float,
    missing_evidence_fraction: float,
    relative_uncertainty: float,
    staleness: float,
    expected_voi: float = 0.0,
    resilience_model_calibrated: bool = False,
) -> dict[str, Any]:
    """Keep uncertainty out of potential-hazard score and inside observation priority."""
    anomaly = _unit(current_anomaly, "current_anomaly")
    consequence = _unit(potential_consequence, "potential_consequence")
    missing = _unit(missing_evidence_fraction, "missing_evidence_fraction")
    uncertainty = _unit(relative_uncertainty, "relative_uncertainty")
    stale = _unit(staleness, "staleness")
    voi = _unit(expected_voi, "expected_voi")
    vulnerability = (
        _unit(resilience_vulnerability, "resilience_vulnerability") if resilience_vulnerability is not None else None
    )
    hazard_components = {
        "current_anomaly": 0.4 * anomaly,
        "potential_consequence": 0.35 * consequence,
        "resilience_vulnerability": 0.25 * vulnerability if vulnerability is not None else 0.0,
    }
    available_weight = 0.75 + (0.25 if vulnerability is not None else 0.0)
    hazard_score = sum(hazard_components.values()) / available_weight
    observation_components = {
        "missing_evidence": 0.35 * missing,
        "relative_uncertainty": 0.3 * uncertainty,
        "staleness": 0.15 * stale,
        "expected_voi": 0.2 * voi,
    }
    observation_score = sum(observation_components.values())
    return {
        "hazard_priority": {
            "score": hazard_score,
            "components": hazard_components,
            "status": (
                "calibrated_resilience_screening"
                if resilience_vulnerability is not None and resilience_model_calibrated
                else "model_based_priority_not_event_probability"
            ),
            "uncertainty_increases_score": False,
        },
        "observation_priority": {
            "score": observation_score,
            "components": observation_components,
            "status": "evidence_acquisition_priority",
        },
        "safety_statement": "Neither score is a probability of failure or an official warning.",
    }
