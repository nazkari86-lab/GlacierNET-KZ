"""Security headers middleware — CSP, HSTS, X-Frame-Options, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


@dataclass
class SecurityHeadersConfig:
    """Security headers configuration."""

    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'"
    )
    strict_transport_security: str = "max-age=63072000; includeSubDomains; preload"
    x_content_type_options: str = "nosniff"
    x_frame_options: str = "DENY"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "camera=(), microphone=(), geolocation=()"
    x_permitted_cross_domain_policies: str = "none"
    cross_origin_embedder_policy: str = "require-corp"
    cross_origin_opener_policy: str = "same-origin"
    cross_origin_resource_policy: str = "same-origin"
    server_header: bool = False
    remove_powered_by: bool = True
    custom_headers: dict[str, str] = field(default_factory=dict)
    exempt_paths: list[str] = field(default_factory=lambda: ["/health"])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects security headers into all responses."""

    def __init__(self, app, config: Optional[SecurityHeadersConfig] = None):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path
        for exempt in self.config.exempt_paths:
            if path.startswith(exempt):
                return response

        response.headers["content-security-policy"] = self.config.content_security_policy
        response.headers["strict-transport-security"] = self.config.strict_transport_security
        response.headers["x-content-type-options"] = self.config.x_content_type_options
        response.headers["x-frame-options"] = self.config.x_frame_options
        response.headers["x-xss-protection"] = self.config.x_xss_protection
        response.headers["referrer-policy"] = self.config.referrer_policy
        response.headers["permissions-policy"] = self.config.permissions_policy
        response.headers["x-permitted-cross-domain-policies"] = self.config.x_permitted_cross_domain_policies
        response.headers["cross-origin-embedder-policy"] = self.config.cross_origin_embedder_policy
        response.headers["cross-origin-opener-policy"] = self.config.cross_origin_opener_policy
        response.headers["cross-origin-resource-policy"] = self.config.cross_origin_resource_policy

        if self.config.remove_powered_by and "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]
        if not self.config.server_header and "server" in response.headers:
            del response.headers["server"]

        for name, value in self.config.custom_headers.items():
            response.headers[name] = value

        return response
