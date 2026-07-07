"""Tests for app/auth/jwt_auth.py — JWTAuth, JWTConfig, TokenPayload, HS256."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.auth.jwt_auth import (
    JWTAuth,
    JWTConfig,
    TokenPayload,
    _b64url_decode,
    _b64url_encode,
    _sign_hs256,
    create_jwt_auth,
)


@pytest.fixture
def jwt_auth():
    return JWTAuth(JWTConfig(secret="test_secret_key_12345", algorithm="HS256"))


@pytest.fixture
def jwt_auth_with_expiry():
    return JWTAuth(JWTConfig(
        secret="test_secret_key_12345",
        algorithm="HS256",
        access_token_ttl=1,
        refresh_token_ttl=2,
    ))


class TestB64UrlEncode:
    def test_encode_decode_roundtrip(self):
        data = b"hello world"
        encoded = _b64url_encode(data)
        decoded = _b64url_decode(encoded)
        assert decoded == data

    def test_encode_string(self):
        result = _b64url_encode(b"test")
        assert isinstance(result, str)
        assert "=" not in result


class TestSignHs256:
    def test_deterministic(self):
        s1 = _sign_hs256("data", "secret")
        s2 = _sign_hs256("data", "secret")
        assert s1 == s2

    def test_different_secrets(self):
        s1 = _sign_hs256("data", "secret1")
        s2 = _sign_hs256("data", "secret2")
        assert s1 != s2


class TestTokenPayload:
    def test_to_dict(self):
        payload = TokenPayload(
            sub="user1",
            exp=1000.0,
            iat=900.0,
            iss="test",
            aud="test-api",
            scopes=["read"],
            role="viewer",
            token_id="abc",
            type="access",
        )
        d = payload.to_dict()
        assert d["sub"] == "user1"
        assert d["exp"] == 1000
        assert d["iat"] == 900
        assert d["jti"] == "abc"
        assert d["type"] == "access"
        assert d["scopes"] == ["read"]

    def test_from_dict(self):
        d = {
            "sub": "user1",
            "exp": 1000.0,
            "iat": 900.0,
            "iss": "test",
            "aud": "test-api",
            "scopes": ["read"],
            "role": "viewer",
            "jti": "abc",
            "type": "access",
        }
        payload = TokenPayload.from_dict(d)
        assert payload.sub == "user1"
        assert payload.exp == 1000.0
        assert payload.token_id == "abc"

    def test_from_dict_defaults(self):
        d = {"sub": "user1", "exp": 1000.0, "iat": 900.0}
        payload = TokenPayload.from_dict(d)
        assert payload.iss == ""
        assert payload.scopes == []
        assert payload.role == "viewer"
        assert payload.type == "access"


class TestJWTAuth:
    def test_default_config_generates_secret(self):
        auth = JWTAuth()
        assert auth.config.secret != ""

    def test_create_access_token(self, jwt_auth):
        token = jwt_auth.create_access_token("user1", scopes=["read"], role="viewer")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_refresh_token(self, jwt_auth):
        token = jwt_auth.create_refresh_token("user1", role="viewer")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_decode_token_roundtrip(self, jwt_auth):
        token = jwt_auth.create_access_token("user1", scopes=["read", "write"], role="analyst")
        payload = jwt_auth.decode_token(token)
        assert payload.sub == "user1"
        assert "read" in payload.scopes
        assert "write" in payload.scopes
        assert payload.role == "analyst"
        assert payload.type == "access"

    def test_decode_refresh_token(self, jwt_auth):
        token = jwt_auth.create_refresh_token("user1", role="admin")
        payload = jwt_auth.decode_token(token)
        assert payload.sub == "user1"
        assert payload.type == "refresh"
        assert payload.role == "admin"

    def test_decode_invalid_token(self, jwt_auth):
        with pytest.raises(HTTPException) as exc_info:
            jwt_auth.decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_decode_malformed_token(self, jwt_auth):
        with pytest.raises(HTTPException) as exc_info:
            jwt_auth.decode_token("not-a-jwt")
        assert exc_info.value.status_code == 401

    def test_decode_wrong_secret(self, jwt_auth):
        token = jwt_auth.create_access_token("user1")
        auth2 = JWTAuth(JWTConfig(secret="wrong_secret_key_99999", algorithm="HS256"))
        with pytest.raises(HTTPException) as exc_info:
            auth2.decode_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_expired_token(self, jwt_auth_with_expiry):
        token = jwt_auth_with_expiry.create_access_token("user1")
        import time
        time.sleep(1.1)
        with pytest.raises(HTTPException) as exc_info:
            jwt_auth_with_expiry.decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_revoke_token(self, jwt_auth):
        token = jwt_auth.create_access_token("user1")
        payload = jwt_auth.decode_token(token)
        jwt_auth.revoke_token(payload.token_id)
        with pytest.raises(HTTPException) as exc_info:
            jwt_auth.decode_token(token)
        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail

    def test_rotate_refresh_token(self, jwt_auth):
        old_refresh = jwt_auth.create_refresh_token("user1")
        new_access, new_refresh = jwt_auth.rotate_refresh_token(old_refresh)
        assert isinstance(new_access, str)
        assert isinstance(new_refresh, str)
        assert new_access != old_refresh
        assert new_refresh != old_refresh

    def test_rotate_non_refresh_token_raises(self, jwt_auth):
        access = jwt_auth.create_access_token("user1")
        with pytest.raises(HTTPException) as exc_info:
            jwt_auth.rotate_refresh_token(access)
        assert exc_info.value.status_code == 400

    def test_validate_scope(self, jwt_auth):
        token = jwt_auth.create_access_token("user1", scopes=["read", "write"])
        assert jwt_auth.validate_scope(token, "read") is True
        assert jwt_auth.validate_scope(token, "admin") is False

    def test_validate_scope_admin(self, jwt_auth):
        token = jwt_auth.create_access_token("user1", scopes=["admin"])
        assert jwt_auth.validate_scope(token, "any_scope") is True

    def test_create_token_pair(self, jwt_auth):
        tokens = jwt_auth.create_token_pair("user1", scopes=["read"], role="viewer")
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert "expires_in" in tokens


class TestCreateJwtAuth:
    def test_creates_auth_with_random_secret(self):
        auth = create_jwt_auth()
        assert isinstance(auth, JWTAuth)
        assert auth.config.algorithm == "HS256"
