"""Scientific cockpit data must remain artifact-bound and fail closed."""


def test_scientific_evidence_exposes_scope_and_claim_boundaries():
    from app.services.scientific_evidence_service import scientific_evidence

    payload = scientific_evidence()

    assert payload["schema"] == "glaciernet-kz.scientific-evidence.v1"
    assert payload["temporal_holdout"]["label_quality_tier"] == "silver"
    assert payload["temporal_holdout"]["splits"]["test_years"] == [2024]
    assert payload["temporal_holdout"]["glacier_level_ci_status"].startswith("blocked")
    assert payload["paired_glacier_diagnostic"]["evaluation_status"] == "post_hoc_non_independent_not_a_holdout"
    assert payload["paired_glacier_diagnostic"]["metrics"]["hard_iou"]["n_glaciers"] == 18
    assert payload["external_safeguard"]["parameters_frozen_before_external_replay"] is True
    assert (
        payload["external_safeguard"]["safeguard"]["hard_dice"]["estimate"]
        > payload["external_safeguard"]["baseline"]["hard_dice"]["estimate"]
    )
    assert "not independent" in payload["external_safeguard"]["circularity_guard"]
    assert any(claim["status"] == "blocked_external_evidence" for claim in payload["claim_registry"])
    assert any(claim["status"] == "refuted_for_current_model" for claim in payload["claim_registry"])


def test_claim_registry_returns_existing_artifacts_with_digests_only():
    from app.services.scientific_evidence_service import scientific_evidence

    payload = scientific_evidence()
    claims = {claim["id"]: claim for claim in payload["claim_registry"]}

    assert claims["C1"]["artifacts"]
    assert all(item["exists"] for item in claims["C1"]["artifacts"])
    assert all(len(item["sha256"]) == 64 for item in claims["C1"]["artifacts"])
    assert claims["C5"]["status"] == "blocked_external_evidence"
    assert "authoritative regional boundary" in claims["C5"]["scope"]
    assert claims["C8"]["status"] == "supported_provisional"
    assert all(item["exists"] for item in claims["C8"]["artifacts"])
