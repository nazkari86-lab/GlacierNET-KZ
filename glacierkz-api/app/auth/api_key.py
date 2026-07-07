"""API key authentication — header and query parameter based."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_key(prefix: str = "gkz") -> str:
    raw = secrets.token_urlsafe(32)
    return f"{prefix}_{raw}"


@dataclass
class APIKeyEntry:
    key_hash: str
    name: str
    scopes: list[str] = field(default_factory=lambda: ["read"])
    rate_limit_override: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    disabled: bool = False

    @property
    def is_valid(self) -> bool:
        if self.disabled:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True


_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_query = APIKeyQuery(name="api_key", auto_error=False)


class APIKeyAuth:
    """API key store with validation, hashing, and scope checking."""

    def __init__(self):
        self._keys: dict[str, APIKeyEntry] = {}

    def add_key(
        self,
        raw_key: str,
        name: str,
        scopes: list[str] | None = None,
        rate_limit_override: int | None = None,
        expires_in: float | None = None,
    ) -> APIKeyEntry:
        key_hash = _hash_key(raw_key)
        entry = APIKeyEntry(
            key_hash=key_hash,
            name=name,
            scopes=scopes or ["read"],
            rate_limit_override=rate_limit_override,
            expires_at=time.time() + expires_in if expires_in else None,
        )
        self._keys[key_hash] = entry
        return entry

    def remove_key(self, raw_key: str) -> bool:
        key_hash = _hash_key(raw_key)
        if key_hash in self._keys:
            del self._keys[key_hash]
            return True
        return False

    def disable_key(self, raw_key: str) -> bool:
        key_hash = _hash_key(raw_key)
        entry = self._keys.get(key_hash)
        if entry:
            entry.disabled = True
            return True
        return False

    def validate(self, raw_key: str) -> Optional[APIKeyEntry]:
        key_hash = _hash_key(raw_key)
        entry = self._keys.get(key_hash)
        if entry and entry.is_valid:
            return entry
        return None

    def get_scopes(self, raw_key: str) -> list[str]:
        entry = self.validate(raw_key)
        return entry.scopes if entry else []

    def has_scope(self, raw_key: str, scope: str) -> bool:
        return scope in self.get_scopes(raw_key)

    def list_keys(self) -> list[dict]:
        return [
            {
                "name": e.name,
                "scopes": e.scopes,
                "created_at": e.created_at,
                "expires_at": e.expires_at,
                "disabled": e.disabled,
            }
            for e in self._keys.values()
        ]

    async def __call__(self, header: str = Security(_header), query: str = Security(_query)) -> str:
        raw = header or query
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required (X-API-Key header or api_key query param)",
                headers={"WWW-Authenticate": "ApiKey"},
            )
        entry = self.validate(raw)
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API key",
            )
        return raw


api_key_auth = APIKeyAuth()
