import json

from fastapi.testclient import TestClient

from app.main import app


def test_service_rejects_invalid_passport(monkeypatch, tmp_path):
    from app.services import cryogenesis_service

    root = tmp_path / "cryogenesis"
    (root / "passports").mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"cohort_id": "broken"}))
    (root / "passports" / "RGI-A.json").write_text(
        json.dumps({"schema": "bad"})
    )
    monkeypatch.setattr(cryogenesis_service, "CRYOGENESIS_ROOT", root)

    result = cryogenesis_service.get_passport("RGI-A")
    assert result["status"] == "invalid_artifact"
    assert result["claims_not_allowed"]


def test_router_returns_404_without_nearest_glacier_substitution(
    monkeypatch,
    tmp_path,
):
    from app.services import cryogenesis_service

    root = tmp_path / "cryogenesis"
    (root / "passports").mkdir(parents=True)
    monkeypatch.setattr(cryogenesis_service, "CRYOGENESIS_ROOT", root)
    with TestClient(app) as client:
        response = client.get(
            "/api/cryogenesis/glaciers/UNKNOWN/passport"
        )
        assert response.status_code == 404
