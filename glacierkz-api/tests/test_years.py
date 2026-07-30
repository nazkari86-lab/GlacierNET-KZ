"""Tests for read-only, local yearly result exploration."""

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routers import years as years_router

client = TestClient(app)


def test_list_years_uses_verified_tables():
    response = client.get("/api/years")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 15
    years = {item["year"]: item for item in body["years"]}
    assert 2000 in years
    assert 2024 in years
    assert years[2015]["include_in_strict_trend"] is False
    assert years[2024]["quality_score"] < 100
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"


def test_strict_years_exclude_low_quality_2015():
    response = client.get("/api/years?strict_only=true")
    assert response.status_code == 200
    assert 2015 not in {item["year"] for item in response.json()["years"]}


def test_compare_years_returns_caveated_change():
    response = client.get("/api/years/compare?from_year=2000&to_year=2024")
    assert response.status_code == 200
    body = response.json()
    assert body["from"]["year"] == 2000
    assert body["to"]["year"] == 2024
    assert body["change_km2"] == -128.61
    assert body["comparable_in_strict_trend"] is False
    assert body["warnings"]


def test_unknown_year_is_404():
    assert client.get("/api/years/1999").status_code == 404


def test_missing_physical_map_layer_is_a_typed_availability_result(monkeypatch):
    def missing_layer(_year: int):
        raise HTTPException(404, "No physical map mask is available")

    monkeypatch.setattr(years_router, "_map_layer_metadata", missing_layer)

    payload = years_router.map_layer_metadata(2024)

    assert payload["available"] is False
    assert payload["year"] == 2024
    assert "physical map mask" in payload["reason"]
    assert "image_url" not in payload
