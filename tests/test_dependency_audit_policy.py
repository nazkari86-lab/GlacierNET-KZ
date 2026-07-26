from datetime import date

import pytest

from scripts.audit_dependencies import load_active_exception_ids


def test_security_exception_registry_is_active_and_unique():
    ids = load_active_exception_ids(date(2026, 7, 26))
    assert ids
    assert len(ids) == len(set(ids))


def test_security_exception_registry_expires_closed():
    with pytest.raises(RuntimeError, match="expired"):
        load_active_exception_ids(date(2026, 8, 10))
