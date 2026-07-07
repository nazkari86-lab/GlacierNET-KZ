"""Optional API-key gate for /api/admin routes."""

from __future__ import annotations

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.auth.admin import admin_api_key_auth
from app.config import ADMIN_API_KEY


class AdminAuthMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key when ADMIN_API_KEY is configured."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Non-admin routes always pass through.
        if not request.url.path.startswith("/api/admin"):
            return await call_next(request)

        # Admin routes require ADMIN_API_KEY to be configured.
        if not ADMIN_API_KEY:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Admin API is not configured (ADMIN_API_KEY not set)"},
            )

        raw_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if not raw_key or not admin_api_key_auth.validate(raw_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Admin API key required (X-API-Key header or api_key query param)"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return await call_next(request)
