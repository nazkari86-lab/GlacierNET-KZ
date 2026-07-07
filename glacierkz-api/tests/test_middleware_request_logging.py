"""Tests for app/middleware/request_logging.py — RequestLoggingMiddleware, RequestLoggingConfig."""

from __future__ import annotations

import logging

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.request_logging import RequestLoggingConfig, RequestLoggingMiddleware


@pytest.fixture
def app_with_logging():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    @app.get("/excluded")
    async def excluded():
        return {"excluded": True}

    @app.post("/data")
    async def create_data():
        return {"created": True}

    config = RequestLoggingConfig(
        exclude_paths=["/excluded"],
        log_request_body=True,
        max_body_log_length=100,
        sensitive_headers=["authorization", "x-api-key"],
    )
    app.add_middleware(RequestLoggingMiddleware, config=config)
    return app


@pytest.fixture
def app_no_exclude():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    config = RequestLoggingConfig()
    app.add_middleware(RequestLoggingMiddleware, config=config)
    return app


class TestRequestLoggingConfig:
    def test_default_values(self):
        cfg = RequestLoggingConfig()
        assert "/health" in cfg.exclude_paths
        assert "/metrics" in cfg.exclude_paths
        assert cfg.log_request_body is False
        assert cfg.max_body_log_length == 500
        assert "authorization" in cfg.sensitive_headers
        assert "cookie" in cfg.sensitive_headers


class TestRequestLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logs_get_request(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.get("/data")
        # extra fields are stored on the LogRecord, not in caplog.text
        records = [r for r in caplog.records if r.name == "glacierkz.access"]
        assert len(records) >= 1
        rec = records[-1]
        assert rec.method == "GET"
        assert rec.path == "/data"

    @pytest.mark.asyncio
    async def test_logs_post_request(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.post("/data")
        records = [r for r in caplog.records if r.name == "glacierkz.access"]
        assert len(records) >= 1
        rec = records[-1]
        assert rec.method == "POST"
        assert rec.path == "/data"

    @pytest.mark.asyncio
    async def test_excluded_path_skipped(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.get("/excluded")
        assert "/excluded" not in caplog.text or "excluded" not in caplog.text

    @pytest.mark.asyncio
    async def test_request_id_generated(self, app_with_logging):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            r = await client.get("/data")
            assert "X-Request-ID" in r.headers

    @pytest.mark.asyncio
    async def test_existing_request_id_preserved(self, app_with_logging):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            r = await client.get("/data", headers={"X-Request-ID": "existing-id"})
            assert r.headers["X-Request-ID"] == "existing-id"

    @pytest.mark.asyncio
    async def test_response_time_header(self, app_with_logging):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            r = await client.get("/data")
            assert "X-Response-Time" in r.headers

    @pytest.mark.asyncio
    async def test_sensitive_headers_masked(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.get("/data", headers={"Authorization": "Bearer secret123"})
        assert "secret123" not in caplog.text

    @pytest.mark.asyncio
    async def test_no_exclude_paths(self, app_no_exclude):
        async with AsyncClient(transport=ASGITransport(app=app_no_exclude), base_url="http://test") as client:
            r = await client.get("/data")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_request_with_body(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.post("/data", json={"key": "value"})
        records = [r for r in caplog.records if r.name == "glacierkz.access"]
        assert len(records) >= 1
        rec = records[-1]
        assert rec.method == "POST"
        assert rec.path == "/data"

    @pytest.mark.asyncio
    async def test_max_body_length_truncation(self, app_with_logging, caplog):
        async with AsyncClient(transport=ASGITransport(app=app_with_logging), base_url="http://test") as client:
            with caplog.at_level(logging.DEBUG, logger="glacierkz.access"):
                await client.post("/data", json={"key": "x" * 200})
        records = [r for r in caplog.records if r.name == "glacierkz.access"]
        assert len(records) >= 1
        rec = records[-1]
        assert rec.method == "POST"
