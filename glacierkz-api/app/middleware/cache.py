"""Cache middleware for GET requests with configurable TTL."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


@dataclass
class CacheConfig:
    """Cache middleware configuration."""

    default_ttl: int = 300
    max_size: int = 1000
    exempt_paths: list[str] = field(default_factory=lambda: ["/health", "/docs"])
    cache_control_header: bool = True
    vary_headers: list[str] = field(default_factory=lambda: ["Authorization", "Accept-Language"])
    key_func: Optional[Callable[[Request], str]] = None


class _CacheEntry:
    __slots__ = ("data", "headers", "status", "expires")

    def __init__(self, data: bytes, headers: dict, status: int, expires: float):
        self.data = data
        self.headers = headers
        self.status = status
        self.expires = expires

    @property
    def is_valid(self) -> bool:
        return time.monotonic() < self.expires


class CacheMiddleware(BaseHTTPMiddleware):
    """In-memory HTTP cache for GET requests with ETag support."""

    def __init__(self, app, config: Optional[CacheConfig] = None):
        super().__init__(app)
        self.config = config or CacheConfig()
        self._cache: dict[str, _CacheEntry] = {}

    def _build_key(self, request: Request) -> str:
        if self.config.key_func:
            return self.config.key_func(request)
        parts = [request.method, str(request.url)]
        for h in self.config.vary_headers:
            parts.append(f"{h}:{request.headers.get(h, '')}")
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _evict_expired(self) -> None:
        if len(self._cache) > self.config.max_size:
            time.monotonic()
            expired = [k for k, v in self._cache.items() if not v.is_valid]
            for k in expired:
                del self._cache[k]
            if len(self._cache) > self.config.max_size:
                oldest = sorted(self._cache, key=lambda k: self._cache[k].expires)
                for k in oldest[: len(oldest) // 2]:
                    del self._cache[k]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        for exempt in self.config.exempt_paths:
            if path.startswith(exempt):
                return await call_next(request)

        if request.method == "GET":
            cache_key = self._build_key(request)
            entry = self._cache.get(cache_key)
            if entry and entry.is_valid:
                if_none_match = request.headers.get("if-none-match")
                etag = entry.headers.get("etag")
                if etag and if_none_match == etag:
                    return Response(status_code=304)
                resp = Response(
                    content=entry.data,
                    status_code=entry.status,
                    headers=entry.headers,
                )
                return resp

        response = await call_next(request)

        if request.method == "GET" and response.status_code == 200:
            body = b""
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    body += chunk.encode()
                else:
                    body += chunk

            etag = hashlib.md5(body, usedforsecurity=False).hexdigest()
            headers = dict(response.headers)
            headers["etag"] = f'"{etag}"'
            if self.config.cache_control_header:
                headers["cache-control"] = f"max-age={self.config.default_ttl}"
            headers["x-cache-status"] = "MISS"

            self._evict_expired()
            self._cache[self._build_key(request)] = _CacheEntry(
                data=body,
                headers=headers,
                status=response.status_code,
                expires=time.monotonic() + self.config.default_ttl,
            )

            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
            )

        return response
