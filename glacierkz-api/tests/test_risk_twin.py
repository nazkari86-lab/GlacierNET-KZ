"""API tests for the safety-bounded Active Cryosphere Risk Twin."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_risk_twin_readiness_is_fail_closed():
    response = client.get("/api/risk-twin/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "research_baseline"
    assert "calibrated event probabilities" in body["blocked"]
    assert "not an official warning" in body["safety_statement"]


def test_risk_twin_evaluate_returns_auditable_abstention():
    response = client.post(
        "/api/risk-twin/evaluate",
        json={
            "basin_id": "B001",
            "observations": [
                {
                    "observation_id": "lake-2025",
                    "variable": "lake_area_m2",
                    "value": 125000,
                    "uncertainty_std": 2500,
                    "timestamp": "2025-07-01T00:00:00Z",
                    "sensor": "Sentinel-2",
                }
            ],
            "actions": [
                {
                    "action_id": "acquire-water-level",
                    "label": "Acquire water-level evidence",
                    "target_variables": ["water_level_m"],
                    "expected_observation_variance": {"water_level_m": 0.04},
                }
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision_support"]["abstain"] is True
    assert body["state"]["provenance"][0]["operation"] == "scalar_kalman_update"
    assert body["observation_ranking"][0]["action_id"] == "acquire-water-level"
    assert body["cascade_graph"]["edges"]


def test_risk_twin_rejects_unknown_state_variable():
    response = client.post(
        "/api/risk-twin/evaluate",
        json={
            "basin_id": "B001",
            "observations": [
                {
                    "observation_id": "invalid",
                    "variable": "magic_risk_probability",
                    "value": 1,
                    "uncertainty_std": 0.1,
                    "timestamp": "2025-07-01T00:00:00Z",
                    "sensor": "unknown",
                }
            ],
        },
    )
    assert response.status_code == 422
    assert "magic_risk_probability" in response.json()["detail"]


def test_risk_twin_api_runs_resilience_stress_surface_without_probability_claim():
    response = client.post(
        "/api/risk-twin/evaluate",
        json={
            "basin_id": "B001",
            "observations": [
                {
                    "observation_id": "level",
                    "variable": "water_level_m",
                    "value": 2,
                    "uncertainty_std": 0.1,
                    "timestamp": "2025-07-01T00:00:00Z",
                    "sensor": "field gauge",
                }
            ],
            "stress_model": {
                "coefficients": {"rainfall_mm_24h": 0.02},
                "state_coefficients": {"water_level_m": 0.1},
                "intercept": 0,
                "transition_threshold": 1,
            },
            "stress_scenarios": [
                {
                    "scenario_id": "large-rain",
                    "stresses": {"rainfall_mm_24h": 50},
                    "physical_cost": 0.5,
                }
            ],
            "priority_inputs": {
                "current_anomaly": 0.4,
                "resilience_vulnerability": 0.6,
                "potential_consequence": 0.8,
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["virtual_stress_test"]["claim_status"] == "unvalidated_model_screening"
    assert body["virtual_stress_test"]["resilience_margin"]["class"] == "external_calibration_required"
    assert body["priorities"]["hazard_priority"]["status"] == "model_based_priority_not_event_probability"
