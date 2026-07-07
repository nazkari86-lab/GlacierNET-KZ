"""Tests for app/middleware/rate_limit.py — RateLimitMiddleware, _TokenBucket, RateLimitConfig."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware.rate_limit import RateLimitConfig, RateLimitMiddleware, _TokenBucket


@pytest.fixture
def app_with_rate_limit():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    @app.get("/exempt")
    async def exempt():
        return {"exempt": True}

    config = RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        burst_size=3,
        burst_window=1.0,
        exempt_paths=["/exempt"],
    )
    app.add_middleware(RateLimitMiddleware, config=config)
    return app


class TestRateLimitConfig:
    def test_default_values(self):
        cfg = RateLimitConfig()
        assert cfg.requests_per_minute == 60
        assert cfg.requests_per_hour == 1000
        assert cfg.burst_size == 10
        assert "/health" in cfg.exempt_paths

    def test_get_client_key_with_x_forwarded_for(self, monkeypatch):
        cfg = RateLimitConfig()
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = None
        assert cfg.get_client_key(request) == "1.2.3.4"

    def test_get_client_key_with_client(self):
        cfg = RateLimitConfig()
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        assert cfg.get_client_key(request) == "127.0.0.1"

    def test_get_client_key_fallback(self):
        cfg = RateLimitConfig()
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert cfg.get_client_key(request) == "unknown"

    def test_custom_key_func(self):
        cfg = RateLimitConfig(key_func=lambda r: "custom")
        request = MagicMock()
        request.headers = {}
        assert cfg.get_client_key(request) == "custom"


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_consume_within_capacity(self):
        bucket = _TokenBucket(capacity=5, refill_rate=1.0)
        assert await bucket.consume(1.0) is True
        assert await bucket.consume(1.0) is True

    @pytest.mark.asyncio
    async def test_consume_exceeds_capacity(self):
        bucket = _TokenBucket(capacity=2, refill_rate=0.1)
        assert await bucket.consume(1.0) is True
        assert await bucket.consume(1.0) is True
        assert await bucket.consume(1.0) is False

    @pytest.mark.asyncio
    async def test_tokens_refill(self):
        bucket = _TokenBucket(capacity=5, refill_rate=100.0)
        assert await bucket.consume(5.0) is True
        time.sleep(0.01)
        assert await bucket.consume(1.0) is True

    def test_retry_after_when_enough_tokens(self):
        bucket = _TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.retry_after == 0.0

    def test_retry_after_when_no_tokens(self):
        bucket = _TokenBucket(capacity=1, refill_rate=1.0)
        bucket.tokens = 0.0
        assert bucket.retry_after > 0.0


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, app_with_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_with_rate_limit), base_url="http://test") as client:
            r = await client.get("/data")
            assert r.status_code == 200
            assert "X-RateLimit-Limit" in r.headers
            assert "X-RateLimit-Remaining" in r.headers

    @pytest.mark.asyncio
    async def test_exempts_paths(self, app_with_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_with_rate_limit), base_url="http://test") as client:
            for _ in range(10):
                r = await client.get("/exempt")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, app_with_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_with_rate_limit), base_url="http://test") as client:
            for _ in range(5):
                await client.get("/data")
            r = await client.get("/data")
            assert r.status_code == 429

    @pytest.mark.asyncio
    async def test_rate_limit_response_has_retry_after(self, app_with_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_with_rate_limit), base_url="http://test") as client:
            for _ in range(5):
                await client.get("/data")
            r = await client.get("/data")
            assert "Retry-After" in r.headers

    @pytest.mark.asyncio
    async def test_get_or_create_bucket(self, app_with_rate_limit):
        async with AsyncClient(transport=ASGITransport(app=app_with_rate_limit), base_url="http://test") as client:
            await client.get("/data")


class TestRateLimitMiddlewareEdgeCases:
    @pytest.mark.asyncio
    async def test_hourly_limit(self, monkeypatch):
        app = FastAPI()

        @app.get("/data")
        async def data():
            return {"value": 42}

        config = RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=3,
            burst_size=100,
        )
        app.add_middleware(RateLimitMiddleware, config=config)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for _ in range(5):
                await client.get("/data")
            r = await client.get("/data")
            assert r.status_code == 429

    @pytest.mark.asyncio
    async def test_client_with_no_client_host(self):
        app = FastAPI()

        @app.get("/data")
        async def data():
            return {"value": 42}

        config = RateLimitConfig(burst_size=2)
        app.add_middleware(RateLimitMiddleware, config=config)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/data")
            assert r.status_code == 200
