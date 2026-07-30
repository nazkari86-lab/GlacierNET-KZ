"""Tests for the glacier-first multimodal ML workflow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import ml_workspace as router_module
from app.services.ml_workspace_service import (
    _annotation_review_queue,
    ml_readiness,
    training_dataset_readiness,
)

client = TestClient(app)
TUYUKSU = "RGI2000-v7.0-G-13-33843"


@pytest.mark.local_data
def test_ml_readiness_exposes_only_compatible_physical_years():
    payload = ml_readiness()

    assert payload["status"] == "ready"
    assert payload["recommended_model"] == "temporal_s2_terrain_s1"
    years = {item["year"]: item for item in payload["years"]}
    assert years[2015]["compatible_models"] == []
    assert years[2016]["recommended_model"] == "temporal_s2_terrain"
    assert years[2024]["recommended_model"] == "temporal_s2_terrain_s1"
    best = next(item for item in payload["models"] if item["name"] == payload["recommended_model"])
    assert best["trusted_artifact"] is True
    assert best["benchmark"]["hard_dice"] > 0.9
    assert best["benchmark"]["label_quality_tier"] == "silver"


def test_ml_readiness_api_preserves_claim_boundary():
    response = client.get("/api/ml/readiness")

    assert response.status_code == 200
    body = response.json()
    assert "not independent accuracy" in body["interpretation"]
    assert any("entropy" in step for step in body["workflow"])
    assert body["generalisation_sentinel"]["safeguard_hard_dice"] > body["generalisation_sentinel"][
        "baseline_hard_dice"
    ]
    assert body["generalisation_sentinel"]["claim_tier"] == "provisional_inventory_guided_failure_containment"


@pytest.mark.local_data
def test_training_dataset_is_integrated_without_promoting_provisional_labels():
    payload = training_dataset_readiness()

    assert payload["status"] == "ready"
    assert payload["annotation_status"] == "provisional_not_gold"
    assert payload["split_strategy"] == "glacier_group_spatial_holdout"
    assert payload["patch_count"] == 45
    assert payload["eligible_tasks"] == 25
    assert payload["excluded_tasks"]["total"] == 29
    assert payload["minimum_geometry_coverage"] == 1.0
    assert {payload["splits"][name]["patch_count"] for name in ("train", "val", "test")} == {33, 6}
    memberships = payload["membership"]
    assert len(memberships) == 9
    assert set(memberships.values()) == {"train", "val", "test"}
    assert any("not independently adjudicated gold" in item for item in payload["limitations"])
    assert len(payload["review_queue"]) == 8
    assert payload["review_queue"][0]["review_priority"] == 100
    assert all(item["confidence"] != "high_provisional" for item in payload["review_queue"])
    spatial = payload["spatial_evaluation"]
    assert spatial["status"] == "completed_provisional_not_gold"
    assert spatial["glacier_counts"] == {"train": 5, "val": 2, "test": 2}
    assert spatial["candidate_test"]["hard_iou"] > spatial["baseline_test"]["hard_iou"]
    assert spatial["model_artifact_present"] is True
    assert "independent expert accuracy" in spatial["claims_not_allowed"]


@pytest.mark.local_data
def test_training_dataset_api_and_preview_are_available():
    response = client.get("/api/ml/training-dataset")
    preview = client.get("/api/ml/training-dataset/preview")

    assert response.status_code == 200
    assert response.json()["integrity"]["required_arrays_present"] is True
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert len(preview.content) > 10_000


def test_annotation_review_queue_is_deterministic_and_actionable():
    first = _annotation_review_queue(5)
    second = _annotation_review_queue(5)

    assert first == second
    assert len(first) == 5
    assert all(item["next_action"] for item in first)
    assert [item["review_priority"] for item in first] == sorted(
        [item["review_priority"] for item in first],
        reverse=True,
    )


def test_weighted_pipeline_check_runs_off_event_loop(monkeypatch):
    expected = {
        "schema": "glaciernet-kz.weighted-training-check.v1",
        "status": "verified",
        "metrics": {"loss": 0.3},
        "cache": {"hit": False},
    }

    def fake_check(*, refresh):
        assert refresh is True
        return expected

    monkeypatch.setattr(router_module, "verify_weighted_training_pipeline", fake_check)
    response = client.post("/api/ml/training-dataset/verify", json={"refresh": True})

    assert response.status_code == 200
    assert response.json() == expected


def test_glacier_analysis_endpoint_runs_off_event_loop(monkeypatch):
    expected = {
        "schema": "glaciernet-kz.ml-case.v1",
        "case_id": "a" * 20,
        "year": 2024,
        "metrics": {"rgi_overlap_iou": 0.82},
    }

    def fake_analyze(rgi_id, **kwargs):
        assert rgi_id == TUYUKSU
        assert kwargs == {
            "year": 2024,
            "model_name": "temporal_s2_terrain_s1",
            "use_tta": True,
            "context_m": 400,
            "refresh": False,
        }
        return expected

    monkeypatch.setattr(router_module, "analyze_glacier", fake_analyze)
    response = client.post(
        f"/api/ml/glaciers/{TUYUKSU}/analyze",
        json={
            "year": 2024,
            "model_name": "temporal_s2_terrain_s1",
            "use_tta": True,
            "context_m": 400,
        },
    )

    assert response.status_code == 200
    assert response.json() == expected


def test_glacier_analysis_request_rejects_invalid_context_before_inference():
    response = client.post(
        f"/api/ml/glaciers/{TUYUKSU}/analyze",
        json={"year": 2024, "context_m": 3000},
    )

    assert response.status_code == 422
