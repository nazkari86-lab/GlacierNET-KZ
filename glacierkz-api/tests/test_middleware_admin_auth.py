"""Regression tests for the header-only admin boundary."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.api_key import APIKeyAuth
from app.middleware import admin_auth
from app.middleware.admin_auth import AdminAuthMiddleware


def _admin_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/admin/status")
    async def status():
        return {"status": "ok"}

    @app.get("/api/public")
    async def public():
        return {"status": "public"}

    app.add_middleware(AdminAuthMiddleware)
    return app


@pytest.mark.asyncio
async def test_admin_rejects_query_parameter_key(monkeypatch):
    key = "admin-test-key"
    auth = APIKeyAuth()
    auth.add_key(key, "admin", scopes=["admin"])
    monkeypatch.setattr(admin_auth, "ADMIN_API_KEY", key)
    monkeypatch.setattr(admin_auth, "admin_api_key_auth", auth)

    async with AsyncClient(transport=ASGITransport(app=_admin_app()), base_url="http://test") as client:
        response = await client.get("/api/admin/status", params={"api_key": key})

    assert response.status_code == 401
    assert "X-API-Key header" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_accepts_header_and_leaves_public_path_open(monkeypatch):
    key = "admin-test-key"
    auth = APIKeyAuth()
    auth.add_key(key, "admin", scopes=["admin"])
    monkeypatch.setattr(admin_auth, "ADMIN_API_KEY", key)
    monkeypatch.setattr(admin_auth, "admin_api_key_auth", auth)

    async with AsyncClient(transport=ASGITransport(app=_admin_app()), base_url="http://test") as client:
        admin_response = await client.get("/api/admin/status", headers={"X-API-Key": key})
        public_response = await client.get("/api/public")

    assert admin_response.status_code == 200
    assert public_response.status_code == 200


@pytest.mark.asyncio
async def test_admin_fails_closed_when_no_key_is_configured(monkeypatch):
    monkeypatch.setattr(admin_auth, "ADMIN_API_KEY", "")
    monkeypatch.setattr(admin_auth, "admin_api_key_auth", APIKeyAuth())

    async with AsyncClient(transport=ASGITransport(app=_admin_app()), base_url="http://test") as client:
        response = await client.get("/api/admin/status")

    assert response.status_code == 503
