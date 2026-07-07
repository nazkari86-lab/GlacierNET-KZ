"""API tests for on-disk data coverage endpoint."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("CORE_DIR", str(ROOT))

from app.main import app  # noqa: E402

client = TestClient(app)


def test_data_coverage_endpoint():
    resp = client.get("/api/data/coverage")
    assert resp.status_code == 200
    body = resp.json()
    assert "raw_sentinel2" in body
    assert "predictions" in body
    assert isinstance(body["raw_sentinel2"], list)


def test_glacier_areas_endpoint():
    resp = client.get("/api/data/areas?method=RF")
    assert resp.status_code == 200
    body = resp.json()
    assert "rows" in body
    assert isinstance(body["rows"], list)


def test_decision_readiness_endpoint():
    resp = client.get("/api/data/decision-readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "timeseries" in body
    assert "year_quality" in body
    assert isinstance(body["timeseries"], list)


def test_year_quality_endpoint():
    resp = client.get("/api/data/year-quality")
    assert resp.status_code == 200
    body = resp.json()
    assert "rows" in body
    assert isinstance(body["rows"], list)
