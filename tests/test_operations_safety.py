from __future__ import annotations

from src.operations import assess_domain_shift, next_best_observation


def test_domain_shift_abstains_outside_validated_scope() -> None:
    result = assess_domain_shift(
        out_of_distribution_score=0.2,
        model_disagreement=0.1,
        preprocessing_compatible=True,
        region_in_validation_scope=False,
    )
    assert result["status"] == "abstain_local_validation_required"
    assert "outside_validated_region" in result["blockers"]
    assert "not a hazard score" in result["safety_statement"]


def test_next_best_observation_prioritises_model_disagreement() -> None:
    result = next_best_observation(
        uncertainty=0.5,
        staleness=0.2,
        data_quality_gap=0.2,
        model_disagreement=0.9,
        expected_information_gain=0.8,
        domain_shift_status="review_required",
    )
    assert result["action"] == "targeted_field_or_drone_inspection"
    assert result["requires_human_authorisation"] is True
    assert result["semantics"] == "observation priority, not hazard probability"
