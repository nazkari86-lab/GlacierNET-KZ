import json
from pathlib import Path

import pytest

from src.cryogenesis.divergence import estimate_divergence
from src.cryogenesis.mechanisms import load_mechanism_catalog
from src.cryogenesis.passport import (
    build_passport,
    passport_to_dict,
    verify_passport,
)
from src.cryogenesis.schemas import (
    DivergenceResult,
    MatchResult,
    SourceAsset,
    TwinMatch,
)
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


def passport_payload() -> dict:
    match = MatchResult(
        target_rgi_id="RGI-A",
        status="matched",
        twins=(
            TwinMatch("RGI-B", 0.1, {"area_km2": 0.1}, 0.5),
            TwinMatch("RGI-C", 0.2, {"area_km2": 0.2}, 0.3),
            TwinMatch("RGI-D", 0.3, {"area_km2": 0.3}, 0.2),
        ),
    )
    divergence = DivergenceResult(
        target_outcome=-0.2,
        comparator_outcome=-0.1,
        raw_divergence=-0.1,
        standardized_divergence=-2.0,
        comparator_interval=(-0.12, -0.08),
        leave_one_out_range=(-0.11, -0.09),
    )
    source = SourceAsset("fixture", "fixture.json", "a" * 64, 100)
    passport = build_passport(
        cohort_id="ile-2020-2024-v1",
        target_rgi_id="RGI-A",
        match=match,
        divergence=divergence,
        surprise_class="unexplained_divergence_candidate",
        provenance=(source,),
    )
    return passport_to_dict(passport)


def test_passport_is_canonical_hashed_and_blocks_causal_claims():
    payload = passport_payload()
    assert len(payload["payload_sha256"]) == 64
    assert "causal effect identification" in payload["claims_not_allowed"]
    assert verify_passport(payload).valid


def test_tampered_passport_fails_verification():
    payload = json.loads(json.dumps(passport_payload()))
    payload["divergence"]["raw_divergence"] = 999
    result = verify_passport(payload)
    assert not result.valid
    assert "payload_sha256" in result.errors


def test_release_one_mechanism_catalog_is_complete_and_unscored():
    catalog = load_mechanism_catalog(
        Path("benchmarks/cryogenesis/mechanism_genome.json")
    )
    assert len(catalog) == 10
    assert all("score" not in mechanism for mechanism in catalog)
