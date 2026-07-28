"""Tests for fail-closed canonical evidence-case packages."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _local_context(*_args, **_kwargs):
    return {
        "glacier": {
            "rgi_id": "RGI2000-v7.0-G-13-33843",
            "name": "Tuyuksu",
            "rgi_area_km2": 2.43,
            "geometry": {"type": "Polygon", "coordinates": []},
        },
        "layers": {
            "tien_shan_lakes_2023": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "lake_id": "TS-2023-001",
                            "source": "Tien Shan lake inventory 1990-2023",
                            "inventory_year": 2023,
                            "area_m2": 12345,
                        },
                        "geometry": {"type": "Point", "coordinates": [77.1, 43.0]},
                    }
                ],
            },
            "hma_gli_2015_2018": {"type": "FeatureCollection", "features": []},
        },
        "interpretation": {
            "not_allowed": [
                "event probability",
                "validated lake-to-glacier linkage",
                "official warning",
            ]
        },
        "sources": [{"id": "rgi", "label": "RGI 7.0"}],
    }


def test_evidence_case_returns_only_the_exact_requested_local_lake(monkeypatch):
    import app.services.evidence_case_service as service

    monkeypatch.setattr(service, "risk_twin_context", _local_context)

    response = client.get(
        "/api/evidence-cases/RGI2000-v7.0-G-13-33843?lake_id=TS-2023-001&year=2024&scope=local_inventory"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "glaciernet-kz.evidence-case.v1"
    assert body["resolution"] == "local_case"
    assert body["case"]["lake_id"] == "TS-2023-001"
    assert body["facts"]["lake"]["properties"]["lake_id"] == "TS-2023-001"
    assert "event probability" in body["claim_limits"]


def test_evidence_case_rejects_unverified_lake_link_without_guessing(monkeypatch):
    import app.services.evidence_case_service as service

    monkeypatch.setattr(service, "risk_twin_context", _local_context)

    response = client.get(
        "/api/evidence-cases/RGI2000-v7.0-G-13-33843?lake_id=NOT-A-LOCAL-LAKE&year=2024"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolution"] == "glacier_context_only"
    assert body["case"]["lake_id"] is None
    assert body["facts"]["lake"] is None
    assert "not found in the local context" in body["reason"]


def test_evidence_case_rejects_unknown_scope_before_resolution():
    response = client.get("/api/evidence-cases/RGI2000-v7.0-G-13-33843?scope=guessed_scope")

    assert response.status_code == 422
