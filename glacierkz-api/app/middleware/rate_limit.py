"""Token-bucket rate limiting middleware with Redis or in-memory fallback."""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    burst_window: float = 1.0
    exempt_paths: list[str] = field(default_factory=lambda: ["/health", "/docs", "/openapi.json"])
    key_func: Optional[Callable[[Request], str]] = None
    max_clients: int = 10_000
    client_idle_ttl_seconds: float = 3_600.0
    cleanup_interval_seconds: float = 60.0

    def get_client_key(self, request: Request) -> str:
        if self.key_func:
            return self.key_func(request)
        # X-Forwarded-For is user-controlled unless the immediate peer is a
        # configured reverse proxy.  Do not allow clients to mint rate-limit
        # buckets by changing a request header.
        trusted_proxies = {
            host.strip() for host in os.environ.get("TRUSTED_PROXY_HOSTS", "").split(",") if host.strip()
        }
        forwarded = request.headers.get("x-forwarded-for")
        peer = request.client.host if request.client else ""
        if forwarded and peer in trusted_proxies:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


class _TokenBucket:
    """Token bucket algorithm for rate limiting."""

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: float = 1.0) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    @property
    def retry_after(self) -> float:
        if self.tokens >= 1:
            return 0.0
        return max(0.0, (1 - self.tokens) / self.refill_rate)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter — per-client buckets, in-memory (or Redis)."""

    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self._buckets: dict[str, _TokenBucket] = {}
        self._hourly_counts: dict[str, list[float]] = defaultdict(list)
        self._last_seen: dict[str, float] = {}
        self._last_cleanup = 0.0

    def _remove_client(self, client_key: str) -> None:
        self._buckets.pop(client_key, None)
        self._hourly_counts.pop(client_key, None)
        self._last_seen.pop(client_key, None)

    def _cleanup_idle_clients(self, now: float, *, force: bool = False) -> None:
        if not force and now - self._last_cleanup < self.config.cleanup_interval_seconds:
            return
        stale = [
            key for key, last_seen in self._last_seen.items() if now - last_seen >= self.config.client_idle_ttl_seconds
        ]
        for key in stale:
            self._remove_client(key)
        self._last_cleanup = now

    def _evict_least_recently_seen_client(self) -> None:
        if not self._last_seen:
            return
        oldest_key = min(self._last_seen, key=self._last_seen.__getitem__)
        self._remove_client(oldest_key)

    def _get_or_create_bucket(self, client_key: str) -> _TokenBucket:
        now = time.monotonic()
        self._cleanup_idle_clients(now)
        if client_key not in self._buckets:
            # An attacker must not be able to grow process memory forever by
            # sending requests through a stream of spoofed/real client IPs.
            while len(self._buckets) >= max(1, self.config.max_clients):
                self._evict_least_recently_seen_client()
            refill = self.config.requests_per_minute / 60.0
            self._buckets[client_key] = _TokenBucket(
                capacity=self.config.burst_size,
                refill_rate=refill,
            )
        self._last_seen[client_key] = now
        return self._buckets[client_key]

    def _check_hourly_limit(self, client_key: str) -> bool:
        now = time.time()
        cutoff = now - 3600
        self._hourly_counts[client_key] = [t for t in self._hourly_counts[client_key] if t > cutoff]
        if len(self._hourly_counts[client_key]) >= self.config.requests_per_hour:
            return False
        self._hourly_counts[client_key].append(now)
        return True

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        for exempt in self.config.exempt_paths:
            if path.startswith(exempt):
                return await call_next(request)

        client_key = self.config.get_client_key(request)
        bucket = self._get_or_create_bucket(client_key)

        if not await bucket.consume():
            retry = max(1, int(bucket.retry_after))
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(retry)},
            )

        if not self._check_hourly_limit(client_key):
            return Response(
                content='{"detail":"Hourly rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        remaining = max(0, int(bucket.tokens))
        response.headers["X-RateLimit-Limit"] = str(self.config.burst_size)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
