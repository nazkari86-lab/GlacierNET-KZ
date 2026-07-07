"""Admin API key authentication (optional via ADMIN_API_KEY env)."""

from __future__ import annotations

from app.auth.api_key import APIKeyAuth
from app.config import ADMIN_API_KEY

admin_api_key_auth = APIKeyAuth()

if ADMIN_API_KEY:
    admin_api_key_auth.add_key(ADMIN_API_KEY, "admin", scopes=["admin"])
