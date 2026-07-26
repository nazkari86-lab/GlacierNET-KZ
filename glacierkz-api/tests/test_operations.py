from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth.rbac import Role, User, set_current_user
from app.main import app
from app.storage import operations


@pytest.fixture(autouse=True)
def isolated_operations_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(operations, "OPERATIONS_DB_PATH", tmp_path / "operations.db")
    set_current_user(None)
    yield
    set_current_user(None)


def analyst() -> User:
    return User(
        user_id="analyst-1",
        email="analyst@example.test",
        role=Role.ANALYST,
        scopes=["read", "write"],
        display_name="Test Analyst",
    )


def test_operations_demo_is_non_persistent_and_fail_closed() -> None:
    client = TestClient(app, headers={"x-forwarded-for": "198.51.100.10"})
    response = client.get("/api/operations/demo")
    assert response.status_code == 200
    body = response.json()
    assert body["demo_only"] is True
    assert body["persistence"] == "none"
    assert body["counts"]["inspection_tasks"] == 1
    assert body["audit_chain"]["valid"] is True
    assert "not hazard probabilities" in body["safety_statement"]

    overview = client.get("/api/operations/overview").json()
    assert overview["counts"]["assets"] == 0


def test_operations_writes_require_analyst() -> None:
    client = TestClient(app, headers={"x-forwarded-for": "198.51.100.11"})
    response = client.post(
        "/api/operations/basins",
        json={"name": "Talgar pilot", "region": "Talgar basin"},
    )
    assert response.status_code == 403


def test_current_model_domain_shift_exposes_the_poor_external_result() -> None:
    client = TestClient(app, headers={"x-forwarded-for": "198.51.100.13"})
    response = client.get("/api/operations/domain-shift/current-model")
    assert response.status_code == 200
    body = response.json()
    assert body["hard_dice"]["estimate"] < 0.2
    assert body["status"] == "abstain_local_validation_required"
    assert "official warning" in body["forbidden_use"]


def test_operations_evidence_workflow_and_export_hash() -> None:
    client = TestClient(app, headers={"x-forwarded-for": "198.51.100.12"})
    set_current_user(analyst())
    basin = client.post(
        "/api/operations/basins",
        json={"name": "Talgar pilot", "region": "Talgar basin"},
    )
    assert basin.status_code == 201
    basin_id = basin.json()["id"]

    asset = client.post(
        "/api/operations/assets",
        json={
            "basin_id": basin_id,
            "asset_type": "moraine_lake",
            "name": "Pilot Lake 1",
            "latitude": 43.04,
            "longitude": 77.27,
        },
    )
    assert asset.status_code == 201
    asset_id = asset.json()["id"]

    observation = client.post(
        "/api/operations/observations",
        json={
            "asset_id": asset_id,
            "observation_type": "satellite_scene",
            "observed_at": "2026-07-20T00:00:00Z",
            "source": "Sentinel-2",
            "values": {"area_km2": 0.42},
            "quality_status": "review_required",
            "uncertainty": 0.55,
        },
    )
    assert observation.status_code == 201

    candidate = client.post(
        "/api/operations/change-candidates",
        json={
            "asset_id": asset_id,
            "observation_id": observation.json()["id"],
            "change_type": "candidate_area_change",
            "magnitude": 0.08,
            "uncertainty": 0.55,
            "staleness": 0.2,
            "data_quality_gap": 0.3,
            "model_disagreement": 0.65,
            "expected_information_gain": 0.8,
            "out_of_distribution_score": 0.2,
            "preprocessing_compatible": True,
            "region_in_validation_scope": True,
            "detected_at": "2026-07-21T00:00:00Z",
        },
    )
    assert candidate.status_code == 201
    assert candidate.json()["next_best_observation"]["semantics"].startswith(
        "observation priority"
    )

    task = client.post(
        "/api/operations/inspection-tasks",
        json={
            "asset_id": asset_id,
            "candidate_id": candidate.json()["id"],
            "action_type": candidate.json()["next_action"],
            "priority_score": candidate.json()["priority_score"],
            "rationale": candidate.json()["rationale"],
        },
    )
    assert task.status_code == 201

    field = client.post(
        "/api/operations/field-reports",
        json={
            "task_id": task.json()["id"],
            "asset_id": asset_id,
            "observer": "Field Specialist",
            "observed_at": "2026-07-22T08:00:00Z",
            "latitude": 43.04,
            "longitude": 77.27,
            "measurements": {"water_level_m": 1.2},
            "checklist": {"outlet_visible": True},
            "notes": "Shadow-mode inspection.",
            "signature": "Field Specialist",
        },
    )
    assert field.status_code == 201
    overview = client.get("/api/operations/overview").json()
    assert overview["inspection_tasks"][0]["status"] == "completed"

    case = client.post(
        "/api/operations/evidence-cases",
        json={
            "asset_id": asset_id,
            "title": "Pilot Lake 1 review",
            "summary": "Candidate reviewed using satellite and field evidence.",
            "limitations": "Single shadow-mode field visit; no hazard inference.",
        },
    )
    assert case.status_code == 201

    decision = client.post(
        "/api/operations/decisions",
        json={
            "evidence_case_id": case.json()["id"],
            "decision": "Continue routine monitoring",
            "rationale": "No operational conclusion beyond the reviewed evidence.",
            "decided_by": "Duty Analyst",
            "decided_at": "2026-07-22T12:00:00Z",
        },
    )
    assert decision.status_code == 201

    export = client.get(
        f"/api/operations/evidence-cases/{case.json()['id']}/export"
    )
    assert export.status_code == 200
    assert len(export.headers["x-artifact-sha256"]) == 64
    body = export.json()
    assert body["audit_chain"]["valid"] is True
    assert body["bundle_sha256"] == export.headers["x-artifact-sha256"]
    assert "not an official warning" in body["safety_statement"]
