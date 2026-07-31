"""Admin routes must expose evidence, not an invented control plane."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routers.admin import router


def _admin_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_admin_has_no_placeholder_users_or_audit_events():
    async with AsyncClient(transport=ASGITransport(app=_admin_app()), base_url="http://test") as client:
        users = await client.get("/api/admin/users")
        audit = await client.get("/api/admin/audit")

    assert users.status_code == 200
    assert users.json() == {"users": [], "total": 0}
    assert audit.status_code == 200
    assert audit.json()["entries"] == []


@pytest.mark.asyncio
async def test_admin_rejects_non_persistent_or_destructive_actions():
    async with AsyncClient(transport=ASGITransport(app=_admin_app()), base_url="http://test") as client:
        config = await client.post("/api/admin/config/update", json={"key": "DEBUG", "value": True})
        cleanup = await client.post("/api/admin/maintenance/cleanup")

    assert config.status_code == 409
    assert "read-only" in config.json()["detail"]
    assert cleanup.status_code == 501
    assert "deletion is disabled" in cleanup.json()["detail"]
