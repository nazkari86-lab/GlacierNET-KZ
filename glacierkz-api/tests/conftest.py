"""Shared fixtures for glacierkz-api tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the project root and parent (src/) are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_ROOT.parent
for p in [str(PROJECT_ROOT), str(REPO_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def tmp_results_dir(tmp_path):
    """Provide a temporary RESULTS_DIR."""
    d = tmp_path / "results"
    d.mkdir()
    return d


@pytest.fixture
def tmp_upload_dir(tmp_path):
    """Provide a temporary UPLOAD_DIR."""
    d = tmp_path / "uploads"
    d.mkdir()
    return d
