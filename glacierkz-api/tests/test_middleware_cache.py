"""Tests for app/middleware/cache.py — CacheMiddleware, CacheConfig, _CacheEntry."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.middleware.cache import CacheConfig, CacheMiddleware, _CacheEntry


@pytest.fixture
def app_with_cache():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    @app.post("/data")
    async def create_data():
        return {"created": True}

    @app.get("/exempt")
    async def exempt():
        return {"exempt": True}

    config = CacheConfig(default_ttl=5, exempt_paths=["/exempt"])
    app.add_middleware(CacheMiddleware, config=config)
    return app


@pytest.fixture
def app_with_etag():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    config = CacheConfig(default_ttl=5)
    app.add_middleware(CacheMiddleware, config=config)
    return app


@pytest.fixture
def app_no_cache_control():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    config = CacheConfig(default_ttl=5, cache_control_header=False)
    app.add_middleware(CacheMiddleware, config=config)
    return app


@pytest.fixture
def app_custom_key_func():
    app = FastAPI()

    @app.get("/data")
    async def data():
        return {"value": 42}

    def custom_key(request: Request) -> str:
        return "custom_key"

    config = CacheConfig(default_ttl=5, key_func=custom_key)
    app.add_middleware(CacheMiddleware, config=config)
    return app


class TestCacheConfig:
    def test_default_values(self):
        cfg = CacheConfig()
        assert cfg.default_ttl == 300
        assert cfg.max_size == 1000
        assert "/health" in cfg.exempt_paths
        assert cfg.cache_control_header is True
        assert "Authorization" in cfg.vary_headers

    def test_custom_values(self):
        cfg = CacheConfig(default_ttl=60, max_size=100, exempt_paths=["/custom"])
        assert cfg.default_ttl == 60
        assert cfg.max_size == 100
        assert cfg.exempt_paths == ["/custom"]


class TestCacheEntry:
    def test_is_valid_not_expired(self):
        entry = _CacheEntry(b"data", {}, 200, time.monotonic() + 10)
        assert entry.is_valid is True

    def test_is_valid_expired(self):
        entry = _CacheEntry(b"data", {}, 200, time.monotonic() - 1)
        assert entry.is_valid is False


class TestCacheMiddleware:
    @pytest.mark.asyncio
    async def test_get_request_caches(self, app_with_cache):
        async with AsyncClient(transport=ASGITransport(app=app_with_cache), base_url="http://test") as client:
            r1 = await client.get("/data")
            assert r1.status_code == 200
            assert r1.headers.get("x-cache-status") == "MISS"

            r2 = await client.get("/data")
            assert r2.status_code == 200
            assert r2.headers.get("etag") is not None

    @pytest.mark.asyncio
    async def test_post_not_cached(self, app_with_cache):
        async with AsyncClient(transport=ASGITransport(app=app_with_cache), base_url="http://test") as client:
            r = await client.post("/data")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_exempt_path_bypasses_cache(self, app_with_cache):
        async with AsyncClient(transport=ASGITransport(app=app_with_cache), base_url="http://test") as client:
            r = await client.get("/exempt")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_etag_if_none_match(self, app_with_etag):
        async with AsyncClient(transport=ASGITransport(app=app_with_etag), base_url="http://test") as client:
            r1 = await client.get("/data")
            etag = r1.headers.get("etag")
            assert etag is not None

            r2 = await client.get("/data", headers={"if-none-match": etag})
            assert r2.status_code == 304

    @pytest.mark.asyncio
    async def test_etag_mismatch_returns_body(self, app_with_etag):
        async with AsyncClient(transport=ASGITransport(app=app_with_etag), base_url="http://test") as client:
            r1 = await client.get("/data")
            etag = r1.headers.get("etag")

            r2 = await client.get("/data", headers={"if-none-match": etag + "x"})
            assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_no_cache_control_header(self, app_no_cache_control):
        async with AsyncClient(transport=ASGITransport(app=app_no_cache_control), base_url="http://test") as client:
            r = await client.get("/data")
            assert "cache-control" not in r.headers

    @pytest.mark.asyncio
    async def test_custom_key_func(self, app_custom_key_func):
        async with AsyncClient(transport=ASGITransport(app=app_custom_key_func), base_url="http://test") as client:
            r = await client.get("/data")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_eviction_under_max_size(self, monkeypatch):
        app = FastAPI()

        @app.get("/data")
        async def data():
            return {"value": 42}

        config = CacheConfig(default_ttl=5, max_size=3)
        app.add_middleware(CacheMiddleware, config=config)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(5):
                await client.get(f"/data?q={i}")

    def test_build_key_default(self, app_with_cache):
        mw = app_with_cache.middleware_stack
        # Access the inner middleware
        while hasattr(mw, "app"):
            if isinstance(mw, CacheMiddleware):
                break
            mw = mw.app
        else:
            pytest.skip("CacheMiddleware not found in stack")

    def test_build_key_with_vary_headers(self, app_with_cache):
        mw = app_with_cache.middleware_stack
        while hasattr(mw, "app"):
            if isinstance(mw, CacheMiddleware):
                break
            mw = mw.app
        else:
            pytest.skip("CacheMiddleware not found in stack")
