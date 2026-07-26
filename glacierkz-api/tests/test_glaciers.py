"""Tests for the physical RGI glacier registry and per-glacier series."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TUYUKSU = "RGI2000-v7.0-G-13-33843"


def test_glacier_registry_lists_real_rgi_features():
    response = client.get("/api/glaciers?named_only=true")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 8
    assert any(item["rgi_id"] == TUYUKSU for item in body["glaciers"])


def test_tuyuksu_card_contains_inventory_evidence():
    response = client.get(f"/api/glaciers/{TUYUKSU}")
    assert response.status_code == 200
    body = response.json()
    assert body["name_ru"] == "Ледник Центральный Туюксу"
    assert body["rgi_area_km2"] > 2
    assert body["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert body["wgms_reference"] is True


def test_tuyuksu_ndsi_series_is_computed_from_physical_masks():
    response = client.get(f"/api/glaciers/{TUYUKSU}/timeseries?method=ndsi")
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) >= 16
    assert body["points"][0]["year"] == 2000
    assert body["points"][-1]["year"] == 2024
    assert body["points"][-1]["area_km2"] > 0
    assert body["glacier"]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert body["wgms_points"]
    assert "fixed RGI 2000" in body["caveat"]


def test_unknown_glacier_is_404():
    assert client.get("/api/glaciers/RGI-UNKNOWN").status_code == 404


def test_evidence_card_download_is_caveated_json():
    response = client.get(f"/api/glaciers/{TUYUKSU}/report?method=ndsi")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment;" in response.headers["content-disposition"]
    body = response.json()
    assert body["schema"] == "glaciernet-kz.glacier-report.v1"
    assert "ice volume or water-supply forecast" in body["claims_not_allowed"]
