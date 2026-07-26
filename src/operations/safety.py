"""Fail-closed domain-shift and observation-priority decisions."""

from __future__ import annotations

from typing import Any


def _unit(value: float, name: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise ValueError(f"{name} must be between zero and one")
    return number


def assess_domain_shift(
    *,
    out_of_distribution_score: float,
    model_disagreement: float,
    preprocessing_compatible: bool,
    region_in_validation_scope: bool,
) -> dict[str, Any]:
    """Classify deployment compatibility without converting it into hazard."""
    ood = _unit(out_of_distribution_score, "out_of_distribution_score")
    disagreement = _unit(model_disagreement, "model_disagreement")
    score = 0.55 * ood + 0.45 * disagreement
    blockers: list[str] = []
    if not preprocessing_compatible:
        blockers.append("preprocessing_incompatible")
    if not region_in_validation_scope:
        blockers.append("outside_validated_region")
    if ood >= 0.7:
        blockers.append("high_out_of_distribution_score")
    if disagreement >= 0.7:
        blockers.append("high_model_disagreement")

    if blockers:
        status = "abstain_local_validation_required"
        allowed_use = "data-quality triage and manual review only"
    elif score >= 0.45:
        status = "review_required"
        allowed_use = "change-candidate screening with human review"
    else:
        status = "screening_compatible"
        allowed_use = "change-candidate screening within the declared model scope"
    return {
        "score": score,
        "status": status,
        "blockers": blockers,
        "allowed_use": allowed_use,
        "forbidden_use": "official warning, event probability, or autonomous emergency action",
        "safety_statement": "Domain-shift status is a model-compatibility check, not a hazard score.",
    }


def next_best_observation(
    *,
    uncertainty: float,
    staleness: float,
    data_quality_gap: float,
    model_disagreement: float,
    expected_information_gain: float,
    domain_shift_status: str,
) -> dict[str, Any]:
    """Prioritise the next evidence action and explain every component."""
    components = {
        "uncertainty": 0.25 * _unit(uncertainty, "uncertainty"),
        "staleness": 0.20 * _unit(staleness, "staleness"),
        "data_quality_gap": 0.20 * _unit(data_quality_gap, "data_quality_gap"),
        "model_disagreement": 0.15 * _unit(model_disagreement, "model_disagreement"),
        "expected_information_gain": 0.20 * _unit(expected_information_gain, "expected_information_gain"),
    }
    score = sum(components.values())
    if domain_shift_status == "abstain_local_validation_required":
        action = "expert_review_and_local_calibration"
        reason = "Model compatibility gate failed; collect a local reference before model use."
    elif components["data_quality_gap"] >= 0.12:
        action = "acquire_clear_satellite_scene"
        reason = "Input quality is the largest actionable evidence gap."
    elif components["model_disagreement"] >= 0.09:
        action = "targeted_field_or_drone_inspection"
        reason = "Independent model outputs disagree materially."
    elif components["staleness"] >= 0.12:
        action = "refresh_observation"
        reason = "The latest evidence is stale."
    elif score >= 0.55:
        action = "targeted_field_or_drone_inspection"
        reason = "Combined evidence gaps justify targeted inspection."
    else:
        action = "continue_routine_monitoring"
        reason = "No high-value additional observation is currently supported."
    return {
        "score": score,
        "action": action,
        "reason": reason,
        "components": components,
        "semantics": "observation priority, not hazard probability",
        "requires_human_authorisation": action != "continue_routine_monitoring",
    }
