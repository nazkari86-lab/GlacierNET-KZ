import pytest

from src.cryogenesis.divergence import estimate_divergence
from src.cryogenesis.surprise import classify_surprise


def test_divergence_uses_weighted_comparator_and_leave_one_out():
    result = estimate_divergence(
        target_outcome=-0.20,
        twin_outcomes=(-0.10, -0.08, -0.12),
        weights=(0.5, 0.25, 0.25),
    )
    assert result.comparator_outcome == pytest.approx(-0.10)
    assert result.raw_divergence == pytest.approx(-0.10)
    assert result.comparator_interval == (-0.12, -0.08)
    assert result.leave_one_out_range[0] <= result.leave_one_out_range[1]


def test_wide_measurement_uncertainty_abstains():
    status = classify_surprise(
        match_status="matched",
        target_outcome=-0.20,
        raw_divergence=-0.10,
        comparator_interval=(-0.12, -0.08),
        measurement_uncertainty=0.20,
    )
    assert status == "observation_inconclusive"


def test_too_few_twins_is_comparison_inconclusive():
    assert (
        classify_surprise(
            match_status="limited_match",
            target_outcome=None,
            raw_divergence=None,
            comparator_interval=None,
            measurement_uncertainty=None,
        )
        == "comparison_inconclusive"
    )
