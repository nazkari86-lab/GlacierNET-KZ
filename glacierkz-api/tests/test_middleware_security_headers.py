"""Tests for app/middleware/security_headers.py — SecurityHeadersMiddleware, SecurityHeadersConfig."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.security_headers import SecurityHeadersConfig, SecurityHeadersMiddleware


@pytest.fixture
def app_with_headers():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    @app.get("/exempt")
    async def exempt():
        return {"exempt": True}

    config = SecurityHeadersConfig(
        exempt_paths=["/exempt"],
        strict_transport_security="max-age=3600",
        content_security_policy="default-src 'self'",
        custom_headers={"X-Custom": "test"},
    )
    app.add_middleware(SecurityHeadersMiddleware, config=config)
    return app


@pytest.fixture
def app_no_config():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    app.add_middleware(SecurityHeadersMiddleware)
    return app


class TestSecurityHeadersConfig:
    def test_default_values(self):
        cfg = SecurityHeadersConfig()
        assert "max-age=63072000" in cfg.strict_transport_security
        assert "default-src 'self'" in cfg.content_security_policy
        assert "/health" in cfg.exempt_paths

    def test_custom_values(self):
        cfg = SecurityHeadersConfig(
            strict_transport_security="max-age=100",
            content_security_policy="default-src 'none'",
            exempt_paths=["/custom"],
        )
        assert "max-age=100" in cfg.strict_transport_security
        assert "default-src 'none'" in cfg.content_security_policy
        assert cfg.exempt_paths == ["/custom"]


class TestSecurityHeadersMiddleware:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, app_with_headers):
        async with AsyncClient(transport=ASGITransport(app=app_with_headers), base_url="http://test") as client:
            r = await client.get("/data")
            assert "x-content-type-options" in r.headers
            assert r.headers["x-content-type-options"] == "nosniff"
            assert "x-frame-options" in r.headers
            assert "x-xss-protection" in r.headers
            assert "strict-transport-security" in r.headers
            assert "content-security-policy" in r.headers
            assert "x-custom" in r.headers
            assert r.headers["x-custom"] == "test"

    @pytest.mark.asyncio
    async def test_hsts_max_age(self, app_with_headers):
        async with AsyncClient(transport=ASGITransport(app=app_with_headers), base_url="http://test") as client:
            r = await client.get("/data")
            hsts = r.headers.get("strict-transport-security", "")
            assert "max-age=3600" in hsts

    @pytest.mark.asyncio
    async def test_exempt_path_no_security_headers(self, app_with_headers):
        async with AsyncClient(transport=ASGITransport(app=app_with_headers), base_url="http://test") as client:
            r = await client.get("/exempt")
            assert "x-content-type-options" not in r.headers

    @pytest.mark.asyncio
    async def test_default_config(self, app_no_config):
        async with AsyncClient(transport=ASGITransport(app=app_no_config), base_url="http://test") as client:
            r = await client.get("/data")
            assert "x-content-type-options" in r.headers

    @pytest.mark.asyncio
    async def test_custom_csp(self, monkeypatch):
        app = FastAPI()

        @app.get("/data")
        async def data():
            return {"value": 42}

        config = SecurityHeadersConfig(content_security_policy="default-src 'none'")
        app.add_middleware(SecurityHeadersMiddleware, config=config)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/data")
            assert "'none'" in r.headers.get("content-security-policy", "")
