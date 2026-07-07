"""JWT authentication endpoints — login, refresh, logout."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth.rbac import ROLE_SCOPES, Role, User, get_current_user, get_jwt_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Hardcoded user store (replace with SQLAlchemy DB in production)
# ---------------------------------------------------------------------------
_USERS: dict[str, dict] = {
    os.environ.get("ADMIN_EMAIL", "admin@glacierkz.local"): {
        "password": os.environ.get("ADMIN_PASSWORD", "changeme"),
        "role": "admin",
        "display_name": "Administrator",
    },
    os.environ.get("ANALYST_EMAIL", "analyst@glacierkz.local"): {
        "password": os.environ.get("ANALYST_PASSWORD", "analyst123"),
        "role": "analyst",
        "display_name": "Analyst",
    },
}


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse, summary="Obtain access + refresh tokens")
async def login(credentials: LoginRequest) -> TokenResponse:
    user_record = _USERS.get(credentials.email)
    if not user_record or user_record["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = user_record["role"]
    try:
        role_enum = Role(role)
    except ValueError:
        role_enum = Role.VIEWER
    scopes = ROLE_SCOPES.get(role_enum, ["read"])
    pair = get_jwt_auth().create_token_pair(credentials.email, scopes=scopes, role=role)
    return TokenResponse(**pair)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    access, refresh = get_jwt_auth().rotate_refresh_token(body.refresh_token)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=get_jwt_auth().config.access_token_ttl,
    )


@router.post("/logout", status_code=204, summary="Revoke refresh token")
async def logout(body: RefreshRequest) -> Response:
    try:
        payload = get_jwt_auth().decode_token(body.refresh_token)
        get_jwt_auth().revoke_token(payload.token_id)
    except HTTPException:
        pass
    return Response(status_code=204)


@router.get("/me", summary="Get current user info")
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> dict:
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role.value,
        "scopes": current_user.scopes,
        "display_name": current_user.display_name,
    }
