"""Release package contract tests."""

from __future__ import annotations

import pytest

from scripts.verify_local_release_package import missing_required_paths

pytestmark = pytest.mark.local_data


def test_current_local_release_package_has_all_required_artifacts():
    assert missing_required_paths() == []
