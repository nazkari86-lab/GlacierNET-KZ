"""Tests for app/auth/api_key.py — APIKeyAuth, APIKeyEntry, generate_api_key, _hash_key."""

from __future__ import annotations

import time

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.auth.api_key import (
    APIKeyAuth,
    APIKeyEntry,
    _hash_key,
    api_key_auth,
    generate_api_key,
)


class TestHashKey:
    def test_hash_deterministic(self):
        h1 = _hash_key("test_key")
        h2 = _hash_key("test_key")
        assert h1 == h2

    def test_hash_different_for_different_keys(self):
        h1 = _hash_key("key1")
        h2 = _hash_key("key2")
        assert h1 != h2

    def test_hash_is_hex_string(self):
        h = _hash_key("test")
        int(h, 16)


class TestGenerateApiKey:
    def test_default_prefix(self):
        key = generate_api_key()
        assert key.startswith("gkz_")

    def test_custom_prefix(self):
        key = generate_api_key(prefix="custom")
        assert key.startswith("custom_")

    def test_unique_keys(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestAPIKeyEntry:
    def test_is_valid_not_disabled_not_expired(self):
        entry = APIKeyEntry(key_hash="abc", name="test")
        assert entry.is_valid is True

    def test_is_valid_disabled(self):
        entry = APIKeyEntry(key_hash="abc", name="test", disabled=True)
        assert entry.is_valid is False

    def test_is_valid_expired(self):
        entry = APIKeyEntry(key_hash="abc", name="test", expires_at=time.time() - 10)
        assert entry.is_valid is False

    def test_is_valid_not_yet_expired(self):
        entry = APIKeyEntry(key_hash="abc", name="test", expires_at=time.time() + 100)
        assert entry.is_valid is True

    def test_default_scopes(self):
        entry = APIKeyEntry(key_hash="abc", name="test")
        assert entry.scopes == ["read"]

    def test_custom_scopes(self):
        entry = APIKeyEntry(key_hash="abc", name="test", scopes=["read", "write"])
        assert entry.scopes == ["read", "write"]


class TestAPIKeyAuth:
    def test_add_and_validate(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test")
        assert auth.validate(key) is not None

    def test_validate_invalid_key(self):
        auth = APIKeyAuth()
        assert auth.validate("nonexistent") is None

    def test_remove_key(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test")
        assert auth.remove_key(key) is True
        assert auth.validate(key) is None

    def test_remove_nonexistent(self):
        auth = APIKeyAuth()
        assert auth.remove_key("nonexistent") is False

    def test_disable_key(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test")
        assert auth.disable_key(key) is True
        assert auth.validate(key) is None

    def test_disable_nonexistent(self):
        auth = APIKeyAuth()
        assert auth.disable_key("nonexistent") is False

    def test_get_scopes(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test", scopes=["read", "write"])
        assert auth.get_scopes(key) == ["read", "write"]

    def test_get_scopes_invalid(self):
        auth = APIKeyAuth()
        assert auth.get_scopes("nonexistent") == []

    def test_has_scope(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test", scopes=["read", "write"])
        assert auth.has_scope(key, "read") is True
        assert auth.has_scope(key, "admin") is False

    def test_list_keys(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test")
        keys = auth.list_keys()
        assert len(keys) == 1
        assert keys[0]["name"] == "test"

    def test_expired_key(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test", expires_in=-10)
        assert auth.validate(key) is None

    def test_rate_limit_override(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        entry = auth.add_key(key, name="test", rate_limit_override=100)
        assert entry.rate_limit_override == 100


class TestAPIKeyAuthCallable:
    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self):
        auth = APIKeyAuth()
        app = FastAPI()

        @app.get("/test")
        async def test_route(key: str = Depends(auth)):
            return {"key": key}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/test")
            assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_key(self):
        auth = APIKeyAuth()
        key = generate_api_key()
        auth.add_key(key, name="test")
        app = FastAPI()

        @app.get("/test")
        async def test_route(k: str = Depends(auth)):
            return {"key": k}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/test", headers={"X-API-Key": key})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self):
        auth = APIKeyAuth()
        app = FastAPI()

        @app.get("/test")
        async def test_route(key: str = Depends(auth)):
            return {"key": key}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/test", headers={"X-API-Key": "invalid"})
            assert r.status_code == 401


class TestGlobalApiKeyAuth:
    def test_instance_exists(self):
        assert isinstance(api_key_auth, APIKeyAuth)
