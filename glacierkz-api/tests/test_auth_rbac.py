"""Tests for app/auth/rbac.py — Role, User, RBACDependency, get_current_user, etc."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.auth.rbac import (
    ROLE_SCOPES,
    RBACDependency,
    Role,
    User,
    get_current_user,
    get_minimum_role,
    require_role,
    require_scope,
    set_current_user,
    user_has_role,
    user_has_scope,
)


@pytest.fixture(autouse=True)
def reset_current_user():
    """Reset the global _current_user after each test."""
    set_current_user(None)
    yield
    set_current_user(None)


class TestRole:
    def test_viewer_value(self):
        assert Role.VIEWER.value == "viewer"

    def test_analyst_value(self):
        assert Role.ANALYST.value == "analyst"

    def test_admin_value(self):
        assert Role.ADMIN.value == "admin"

    def test_viewer_level(self):
        assert Role.VIEWER.level == 0

    def test_analyst_level(self):
        assert Role.ANALYST.level == 1

    def test_admin_level(self):
        assert Role.ADMIN.level == 2

    def test_role_comparison(self):
        assert Role.VIEWER.level < Role.ANALYST.level < Role.ADMIN.level


class TestUser:
    def test_is_admin(self):
        user = User(user_id="1", email="a@b.com", role=Role.ADMIN, scopes=["read"])
        assert user.is_admin is True

    def test_is_not_admin(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=["read"])
        assert user.is_admin is False

    def test_is_analyst_when_analyst(self):
        user = User(user_id="1", email="a@b.com", role=Role.ANALYST, scopes=["read"])
        assert user.is_analyst is True

    def test_is_analyst_when_admin(self):
        user = User(user_id="1", email="a@b.com", role=Role.ADMIN, scopes=["read"])
        assert user.is_analyst is True

    def test_is_not_analyst_when_viewer(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=["read"])
        assert user.is_analyst is False


class TestGetMinimumRole:
    def test_read_scope(self):
        assert get_minimum_role("read") == Role.VIEWER

    def test_write_scope(self):
        assert get_minimum_role("write") == Role.ANALYST

    def test_admin_scope(self):
        assert get_minimum_role("admin") == Role.ADMIN

    def test_unknown_scope(self):
        assert get_minimum_role("unknown_scope") == Role.ADMIN


class TestUserHasScope:
    def test_admin_has_any_scope(self):
        user = User(user_id="1", email="a@b.com", role=Role.ADMIN, scopes=[])
        assert user_has_scope(user, "read") is True
        assert user_has_scope(user, "write") is True
        assert user_has_scope(user, "admin") is True
        assert user_has_scope(user, "manage_keys") is True

    def test_analyst_has_write_scope(self):
        user = User(user_id="1", email="a@b.com", role=Role.ANALYST, scopes=[])
        assert user_has_scope(user, "read") is True
        assert user_has_scope(user, "write") is True
        assert user_has_scope(user, "admin") is False

    def test_viewer_only_read(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=[])
        assert user_has_scope(user, "read") is True
        assert user_has_scope(user, "write") is False


class TestUserHasRole:
    def test_viewer_meets_viewer(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=[])
        assert user_has_role(user, Role.VIEWER) is True

    def test_viewer_does_not_meet_admin(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=[])
        assert user_has_role(user, Role.ADMIN) is False

    def test_admin_meets_everything(self):
        user = User(user_id="1", email="a@b.com", role=Role.ADMIN, scopes=[])
        assert user_has_role(user, Role.VIEWER) is True
        assert user_has_role(user, Role.ANALYST) is True
        assert user_has_role(user, Role.ADMIN) is True

    def test_analyst_meets_viewer_and_analyst(self):
        user = User(user_id="1", email="a@b.com", role=Role.ANALYST, scopes=[])
        assert user_has_role(user, Role.VIEWER) is True
        assert user_has_role(user, Role.ANALYST) is True
        assert user_has_role(user, Role.ADMIN) is False


class TestGetCurrentUser:
    def test_default_user(self):
        user = get_current_user()
        assert user.user_id == "anonymous"
        assert user.role == Role.VIEWER

    def test_set_and_get(self):
        custom = User(user_id="custom", email="c@b.com", role=Role.ADMIN, scopes=["read", "write"])
        set_current_user(custom)
        assert get_current_user() is custom

    def test_set_none_returns_default(self):
        set_current_user(None)
        user = get_current_user()
        assert user.user_id == "anonymous"


class TestRequireRole:
    def test_requires_min_role(self):
        dep = require_role(Role.ADMIN)
        assert dep.min_role == Role.ADMIN

    def test_requires_scope(self):
        dep = require_scope("write")
        assert dep.required_scope == "write"


class TestRBACDependency:
    def test_passes_when_role_sufficient(self):
        user = User(user_id="1", email="a@b.com", role=Role.ADMIN, scopes=[])
        dep = RBACDependency(min_role=Role.VIEWER)
        assert dep(user) is user

    def test_raises_when_role_insufficient(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=[])
        dep = RBACDependency(min_role=Role.ADMIN)
        with pytest.raises(HTTPException) as exc_info:
            dep(user)
        assert exc_info.value.status_code == 403

    def test_passes_when_scope_sufficient(self):
        user = User(user_id="1", email="a@b.com", role=Role.ANALYST, scopes=[])
        dep = RBACDependency(required_scope="write")
        assert dep(user) is user

    def test_raises_when_scope_insufficient(self):
        user = User(user_id="1", email="a@b.com", role=Role.VIEWER, scopes=[])
        dep = RBACDependency(required_scope="write")
        with pytest.raises(HTTPException) as exc_info:
            dep(user)
        assert exc_info.value.status_code == 403


class TestRoleScopesMapping:
    def test_viewer_scopes(self):
        assert ROLE_SCOPES[Role.VIEWER] == ["read"]

    def test_analyst_scopes(self):
        assert "read" in ROLE_SCOPES[Role.ANALYST]
        assert "write" in ROLE_SCOPES[Role.ANALYST]
        assert "admin" not in ROLE_SCOPES[Role.ANALYST]

    def test_admin_scopes(self):
        assert "admin" in ROLE_SCOPES[Role.ADMIN]
        assert "delete" in ROLE_SCOPES[Role.ADMIN]
        assert "manage_keys" in ROLE_SCOPES[Role.ADMIN]
