"""Role-based access control — roles, permissions, dependency injection."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status  # Header used in get_current_user default


class Role(str, enum.Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"

    @property
    def level(self) -> int:
        return _ROLE_LEVELS[self]


_ROLE_LEVELS = {
    Role.VIEWER: 0,
    Role.ANALYST: 1,
    Role.ADMIN: 2,
}


@dataclass
class User:
    user_id: str
    email: str
    role: Role
    scopes: list[str]
    display_name: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_analyst(self) -> bool:
        return _ROLE_LEVELS[self.role] >= _ROLE_LEVELS[Role.ANALYST]


# Role → allowed scopes mapping
ROLE_SCOPES: dict[Role, list[str]] = {
    Role.VIEWER: ["read"],
    Role.ANALYST: ["read", "write", "upload", "predict", "export"],
    Role.ADMIN: ["read", "write", "upload", "predict", "export", "admin", "delete", "manage_keys"],
}

# Scope → required role
SCOPE_ROLES: dict[str, Role] = {
    "read": Role.VIEWER,
    "write": Role.ANALYST,
    "upload": Role.ANALYST,
    "predict": Role.ANALYST,
    "export": Role.ANALYST,
    "admin": Role.ADMIN,
    "delete": Role.ADMIN,
    "manage_keys": Role.ADMIN,
}


def get_minimum_role(scope: str) -> Role:
    return SCOPE_ROLES.get(scope, Role.ADMIN)


def user_has_scope(user: User, scope: str) -> bool:
    if user.role == Role.ADMIN:
        return True
    allowed = ROLE_SCOPES.get(user.role, [])
    return scope in allowed


def user_has_role(user: User, required_role: Role) -> bool:
    return _ROLE_LEVELS.get(user.role, 0) >= _ROLE_LEVELS.get(required_role, 2)


class RBACDependency:
    """FastAPI dependency for role/scope-based access control."""

    def __init__(self, min_role: Role | None = None, required_scope: str | None = None):
        self.min_role = min_role
        self.required_scope = required_scope

    def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if self.min_role and not user_has_role(user, self.min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {self.min_role.value} or higher required",
            )
        if self.required_scope and not user_has_scope(user, self.required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{self.required_scope}' required",
            )
        return user


# Default user for unauthenticated access
_default_user = User(
    user_id="anonymous",
    email="",
    role=Role.VIEWER,
    scopes=["read"],
    display_name="Anonymous",
)

_jwt_auth_instance = None
_current_user_override: User | None = None


def set_current_user(user: User | None) -> None:
    """Set an in-process current-user override for tests and local smoke checks."""
    global _current_user_override
    _current_user_override = user


def get_jwt_auth():
    global _jwt_auth_instance
    if _jwt_auth_instance is None:
        from .jwt_auth import create_jwt_auth

        _jwt_auth_instance = create_jwt_auth()
    return _jwt_auth_instance


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User:
    """FastAPI dependency: returns User from Bearer token, or anonymous viewer."""
    if _current_user_override is not None:
        return _current_user_override
    if not authorization or not authorization.startswith("Bearer "):
        return _default_user
    token = authorization[7:]
    try:
        payload = get_jwt_auth().decode_token(token)
    except HTTPException:
        return _default_user
    try:
        role = Role(payload.role)
    except ValueError:
        role = Role.VIEWER
    return User(
        user_id=payload.sub,
        email=payload.sub,
        role=role,
        scopes=ROLE_SCOPES.get(role, ["read"]),
        display_name=payload.sub,
    )


def require_role(role: Role):
    return RBACDependency(min_role=role)


def require_scope(scope: str):
    return RBACDependency(required_scope=scope)
