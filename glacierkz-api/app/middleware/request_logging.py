"""Request logging middleware with structured output and timing."""

from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

_SENSITIVE_KEYS_RE = re.compile(r"(api[_-]?key|token|secret|password)", re.IGNORECASE)

logger = logging.getLogger("glacierkz.access")


@dataclass
class RequestLoggingConfig:
    """Request logging configuration."""

    log_request_body: bool = False
    log_response_body: bool = False
    max_body_log_length: int = 500
    exclude_paths: list[str] = field(default_factory=lambda: ["/health", "/metrics"])
    request_id_header: str = "X-Request-ID"
    generate_request_id: bool = True
    log_level: str = "INFO"
    timing_header: bool = True
    sensitive_headers: list[str] = field(default_factory=lambda: ["authorization", "x-api-key", "cookie"])
    custom_extractor: Optional[Callable[[Request], dict]] = None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with timing, status, and optional body."""

    def __init__(self, app, config: Optional[RequestLoggingConfig] = None):
        super().__init__(app)
        self.config = config or RequestLoggingConfig()

    def _get_request_id(self, request: Request) -> str:
        existing = request.headers.get(self.config.request_id_header)
        if existing:
            return existing
        if self.config.generate_request_id:
            return str(uuid.uuid4())[:16]
        return ""

    def _safe_headers(self, headers: dict) -> dict:
        safe = {}
        for k, v in headers.items():
            if k.lower() in self.config.sensitive_headers:
                safe[k] = "***"
            else:
                safe[k] = v
        return safe

    def _safe_query(self, query_params) -> str:
        """Mask sensitive keys in query string before logging."""
        parts = []
        for k, v in query_params.multi_items():
            if _SENSITIVE_KEYS_RE.search(k):
                parts.append(f"{k}=***")
            else:
                parts.append(f"{k}={v}")
        return "&".join(parts) if parts else ""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        for exc in self.config.exclude_paths:
            if path.startswith(exc):
                return await call_next(request)

        request_id = self._get_request_id(request)
        start = time.monotonic()
        status = 500
        error = None

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            log_data = {
                "method": request.method,
                "path": path,
                "query": self._safe_query(request.query_params),
                "status": status,
                "duration_ms": round(duration_ms, 2),
                "client": request.client.host if request.client else "unknown",
                "request_id": request_id,
            }
            if self.config.custom_extractor:
                log_data.update(self.config.custom_extractor(request))
            if error:
                log_data["error"] = error

            log_fn = logger.info if status < 400 else (logger.warning if status < 500 else logger.error)
            log_fn("request", extra=log_data)

        if request_id:
            response.headers[self.config.request_id_header] = request_id
        if self.config.timing_header:
            response.headers["X-Response-Time"] = f"{round(duration_ms, 2)}ms"

        return response
