"""API tests for the safety-bounded Active Cryosphere Risk Twin."""

import pytest
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


@pytest.mark.local_data
def test_risk_twin_context_exposes_local_spatial_evidence_without_risk_claims():
    response = client.get("/api/risk-twin/context/RGI2000-v7.0-G-13-33843?year=2024&buffer_km=10")
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "glaciernet-kz.risk-twin-context.v4"
    assert body["query"]["lake_inventory_year"] == 2023
    assert body["layers"]["tien_shan_lakes"]["type"] == "FeatureCollection"
    assert body["layers"]["historical_glof_events"]["features"]
    assert body["layers"]["hydrorivers"]["features"]
    assert body["layers"]["hydrobasins_level06"]["features"]
    assert body["downstream_route"]["available"] is True
    assert body["downstream_route"]["features"]["features"]
    assert body["downstream_route"]["route_segment_count"] > 1
    assert body["downstream_route"]["route_length_km"] > 0
    assert body["downstream_route"]["corridor"]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert "not a glacier-to-channel connector" in body["downstream_route"]["interpretation"]
    assert len(body["lake_timeseries"]) == 5
    assert body["impact_assets"]["available"] is True
    assert body["impact_assets"]["features"]["features"]
    assert body["impact_assets"]["returned_feature_count"] <= body["impact_assets"]["map_feature_limit"]
    assert body["impact_assets"]["nearby_asset_count"] >= body["impact_assets"]["returned_feature_count"]
    assert "distance_to_rgi_boundary_m" in body["impact_assets"]["features"]["features"][0]["properties"]
    assert body["jrc_surface_water"]["available"] is True
    assert body["climate_context"]["available"] is True
    assert body["population_planning_context"]["available"] is True
    assert "event probability" in body["interpretation"]["not_allowed"]
    assert "downstream exposure, affected population, evacuation demand, or disruption estimate" in body["interpretation"]["not_allowed"]


@pytest.mark.local_data
def test_risk_twin_context_uses_the_explicit_lake_inventory_year_for_layer_and_candidates():
    response = client.get("/api/risk-twin/context/RGI2000-v7.0-G-13-33843?year=2024&lake_inventory_year=2010")
    assert response.status_code == 200
    body = response.json()
    assert body["query"]["lake_inventory_year"] == 2010
    assert body["query"]["previous_lake_inventory_year"] == 2000
    assert all(candidate["inventory_year"] == 2010 for candidate in body["screening_candidates"])
    assert all(feature["properties"]["inventory_year"] == 2010 for feature in body["layers"]["tien_shan_lakes"]["features"])


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


@pytest.mark.local_data
def test_regional_scan_returns_real_observation_candidates_without_hazard_claims():
    from app.services.risk_twin_context_service import regional_lake_screening

    response = regional_lake_screening(inventory_year=2023, buffer_km=10.0)

    assert response["status"] == "automatic_local_inventory_screening"
    assert response["summary"]["scanned_lakes"] > 0
    assert response["summary"]["candidates_with_nearby_rgi"] == len(response["candidates"])
    candidate = response["candidates"][0]
    assert candidate["glacier"]["rgi_id"].startswith("RGI2000-v7.0")
    assert "hazard" in candidate["interpretation"].lower()


@pytest.mark.local_data
def test_regional_scan_uses_previous_available_inventory_and_keeps_1990_as_baseline():
    from app.services.risk_twin_context_service import regional_lake_screening

    baseline = regional_lake_screening(inventory_year=1990, buffer_km=10.0)
    comparison = regional_lake_screening(inventory_year=2020, buffer_km=10.0)

    assert baseline["previous_inventory_year"] is None
    assert "baseline_inventory_no_earlier_comparison" in baseline["candidates"][0]["flags"]
    assert comparison["previous_inventory_year"] == 2010


def test_follow_up_priority_breakdown_is_bounded_and_not_a_hazard_score():
    from app.services.risk_twin_context_service import _observation_priority_components

    components = _observation_priority_components(
        area_m2=250_000,
        area_change_percent=90,
        distance_to_glacier_m=500,
        previous_match_available=False,
    )

    assert components == {
        "base_follow_up": 20.0,
        "area_change": 40.0,
        "lake_size": 20.0,
        "rgi_proximity": 20.0,
        "no_reliable_previous_match": 20.0,
        "total_before_cap": 120.0,
        "observation_priority_0_100": 100.0,
    }
