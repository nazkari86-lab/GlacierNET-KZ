"""Tests for the explicit ML -> Risk Twin evidence gate."""

import json

import app.services.ml_workspace_service as ml_workspace_service
from app.services.ml_workspace_service import find_ml_case
from app.services.risk_twin_integration_service import integrated_case_decision, ml_evidence_gate


def _candidate(priority: float = 50, area_change: float | None = 8.2):
    return {
        "lake_id": "GL-test",
        "observation_priority_0_100": priority,
        "area_change_percent": area_change,
    }


def _ml_case(*, overlap: float = 0.0193, uncertainty: float = 0.0665, priority: int = 71):
    return {
        "case_id": "a" * 20,
        "metrics": {
            "predicted_area_km2": 0.0009,
            "rgi_overlap_iou": overlap,
            "uncertain_fraction_in_review_zone": uncertainty,
            "review_priority_0_100": priority,
        },
    }


def test_missing_ml_remains_explicit_and_never_changes_lake_priority():
    decision = integrated_case_decision(_candidate(), None)
    assert decision["workflow_priority_0_100"] == 50
    assert decision["driver"] == "missing_ml_evidence"
    assert decision["ml_boundary_review_priority_0_100"] is None
    assert "not hazard" in decision["meaning"]


def test_low_overlap_ml_changes_the_next_task_but_not_into_a_hazard_claim():
    decision = integrated_case_decision(_candidate(), _ml_case())
    assert decision["workflow_priority_0_100"] == 71
    assert decision["driver"] == "ml_boundary_review"
    assert decision["ml_changed_next_action"] is True
    assert decision["gate"]["usable_for_temporal_change"] is False
    assert "0.35" in decision["gate"]["reasons"][0]


def test_screening_gate_accepts_bounded_boundary_but_still_blocks_temporal_change():
    gate = ml_evidence_gate(_ml_case(overlap=0.72, uncertainty=0.08))
    assert gate["status"] == "screening_ready"
    assert gate["usable_for_boundary_screening"] is True
    assert gate["usable_for_temporal_change"] is False


def test_packaged_ales_ml_snapshot_is_real_and_source_digested():
    case = find_ml_case("RGI2000-v7.0-G-13-34154", year=2024, model_name="temporal_s2_terrain_s1")
    assert case is not None
    assert case["case_id"] == "260c89a36fbc7d1cd58b"
    assert len(case["source"]["source_crop_sha256"]) == 64
    assert case["model"]["artifact_sha256"] == "c874443318bc7079b2580ef18e02782e6324d398459bfd55e20f63bc26b83997"
    assert case["metrics"]["review_priority_0_100"] == 71


def test_packaged_snapshot_fails_closed_when_digest_is_wrong(tmp_path, monkeypatch):
    packaged_dir = tmp_path / "packaged"
    runtime_dir = tmp_path / "runtime"
    packaged_dir.mkdir()
    runtime_dir.mkdir()
    case_path = packaged_dir / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "schema": "glaciernet-kz.ml-case.v1",
                "case_id": "b" * 20,
                "glacier": {"rgi_id": "RGI-test"},
                "year": 2024,
                "model": {"name": "temporal_s2_terrain_s1"},
                "created_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    manifest_path = packaged_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "glaciernet-kz.ml-evidence-manifest.v1",
                "cases": [{"file": "case.json", "case_id": "b" * 20, "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ml_workspace_service, "PACKAGED_CASES_DIR", packaged_dir)
    monkeypatch.setattr(ml_workspace_service, "PACKAGED_CASES_MANIFEST", manifest_path)
    monkeypatch.setattr(ml_workspace_service, "CASES_DIR", runtime_dir)

    assert (
        ml_workspace_service.find_ml_case(
            "RGI-test",
            year=2024,
            model_name="temporal_s2_terrain_s1",
        )
        is None
    )
