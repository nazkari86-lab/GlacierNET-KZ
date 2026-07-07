"""JWT authentication — access/refresh tokens, RS256/HS256, claims."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, status


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _sign_hs256(data: str, secret: str) -> str:
    import hmac

    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _sign_rs256(data: str, private_key_pem: str) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    sig = key.sign(data.encode(), padding.PKCS1v15(), hashes.SHA256())
    return _b64url_encode(sig)


@dataclass
class JWTConfig:
    secret: str = ""
    algorithm: str = "HS256"
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    access_token_ttl: int = 900
    refresh_token_ttl: int = 86400 * 7
    issuer: str = "glacierkz"
    audience: str = "glacierkz-api"


@dataclass
class TokenPayload:
    sub: str
    exp: float
    iat: float
    iss: str
    aud: str
    scopes: list[str] = field(default_factory=list)
    role: str = "viewer"
    token_id: str = ""
    type: str = "access"

    def to_dict(self) -> dict:
        return {
            "sub": self.sub,
            "exp": int(self.exp),
            "iat": int(self.iat),
            "iss": self.iss,
            "aud": self.aud,
            "scopes": self.scopes,
            "role": self.role,
            "jti": self.token_id,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TokenPayload:
        return cls(
            sub=d["sub"],
            exp=float(d["exp"]),
            iat=float(d["iat"]),
            iss=d.get("iss", ""),
            aud=d.get("aud", ""),
            scopes=d.get("scopes", []),
            role=d.get("role", "viewer"),
            token_id=d.get("jti", ""),
            type=d.get("type", "access"),
        )


class JWTAuth:
    """Stateless JWT auth with HS256 and RS256 support."""

    def __init__(self, config: Optional[JWTConfig] = None):
        self.config = config or JWTConfig()
        self._revoked: set[str] = set()
        if not self.config.secret:
            self.config.secret = secrets.token_urlsafe(64)

    def _encode(self, payload: dict) -> str:
        header = {"alg": self.config.algorithm, "typ": "JWT"}
        if self.config.algorithm == "RS256" and self.config.private_key:
            header["alg"] = "RS256"

            def sig_fn(data):
                return _sign_rs256(data, self.config.private_key)
        else:

            def sig_fn(data):
                return _sign_hs256(data, self.config.secret)

        h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        sig = sig_fn(f"{h}.{p}")
        return f"{h}.{p}.{sig}"

    def create_access_token(
        self,
        subject: str,
        scopes: list[str] | None = None,
        role: str = "viewer",
        extra: dict | None = None,
    ) -> str:
        now = time.time()
        payload = TokenPayload(
            sub=subject,
            exp=now + self.config.access_token_ttl,
            iat=now,
            iss=self.config.issuer,
            aud=self.config.audience,
            scopes=scopes or [],
            role=role,
            token_id=secrets.token_hex(16),
            type="access",
        )
        d = payload.to_dict()
        if extra:
            d.update(extra)
        return self._encode(d)

    def create_refresh_token(self, subject: str, role: str = "viewer") -> str:
        now = time.time()
        payload = TokenPayload(
            sub=subject,
            exp=now + self.config.refresh_token_ttl,
            iat=now,
            iss=self.config.issuer,
            aud=self.config.audience,
            role=role,
            token_id=secrets.token_hex(16),
            type="refresh",
        )
        return self._encode(payload.to_dict())

    def decode_token(self, token: str) -> TokenPayload:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid token format")
            h_b64, p_b64, sig = parts
            expected_sig = _sign_hs256(f"{h_b64}.{p_b64}", self.config.secret)
            if not secrets.compare_digest(sig, expected_sig):
                raise ValueError("Invalid signature")
            payload = json.loads(_b64url_decode(p_b64))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        if payload.get("jti") in self._revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked",
            )
        now = time.time()
        if payload.get("exp", 0) < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        if payload.get("iss") != self.config.issuer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid issuer",
            )
        return TokenPayload.from_dict(payload)

    def revoke_token(self, token_id: str) -> None:
        self._revoked.add(token_id)

    def rotate_refresh_token(self, old_refresh: str) -> tuple[str, str]:
        payload = self.decode_token(old_refresh)
        if payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not a refresh token",
            )
        self.revoke_token(payload.token_id)
        new_access = self.create_access_token(payload.sub, role=payload.role)
        new_refresh = self.create_refresh_token(payload.sub, role=payload.role)
        return new_access, new_refresh

    def validate_scope(self, token: str, required_scope: str) -> bool:
        payload = self.decode_token(token)
        return required_scope in payload.scopes or "admin" in payload.scopes

    def create_token_pair(
        self,
        subject: str,
        scopes: list[str] | None = None,
        role: str = "viewer",
    ) -> dict[str, str]:
        access = self.create_access_token(subject, scopes=scopes, role=role)
        refresh = self.create_refresh_token(subject, role=role)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": self.config.access_token_ttl,
        }


def create_jwt_auth() -> JWTAuth:
    return JWTAuth(
        JWTConfig(
            secret=secrets.token_urlsafe(64),
            algorithm="HS256",
            access_token_ttl=900,
            refresh_token_ttl=604800,
        )
    )
