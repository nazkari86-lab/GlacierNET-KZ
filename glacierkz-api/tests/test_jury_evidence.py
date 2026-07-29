def test_jury_evidence_keeps_supported_and_blocked_claims_separate():
    from app.services.jury_evidence_service import jury_evidence

    payload = jury_evidence()

    assert payload["release_checks"]["local_package_complete"] is True
    assert payload["supported_now"][0]["value"]["hard_dice"] == 0.874601583120244
    assert payload["supported_now"][0]["value"]["hard_iou"] == 0.7771484036250351
    assert payload["honest_negative_result"]["hard_dice"]["estimate"] < 0.5
    assert any(item["id"] == "C6" for item in payload["blocked_until_external_work"])
    assert payload["automation_readiness"]["machine_assisted_label_pack"]["status"] == "available_provisional_not_gold"
    assert payload["automation_readiness"]["machine_assisted_label_pack"]["tasks"] == 54
    assert payload["automation_readiness"]["machine_assisted_label_pack"]["glaciers"] == 18
    assert payload["automation_readiness"]["machine_assisted_label_pack"]["years"] == [2022, 2023, 2024]
    assert all(not claim["automated_input_ready"] for claim in payload["automation_readiness"]["claims"])
    assert payload["scientific_evidence"]["temporal_holdout"]["splits"]["test_years"] == [2024]
    assert payload["scientific_evidence"]["external_generalisation"]["status"] == "blocked_external_evidence"


def test_jury_endpoint_exposes_the_scientific_cockpit_payload():
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/jury/evidence")

    assert response.status_code == 200
    assert response.json()["scientific_evidence"]["schema"] == "glaciernet-kz.scientific-evidence.v1"
