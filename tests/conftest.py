# -*- coding: utf-8 -*-
"""Session-scoped fixtures and hooks for cleaning up sys.modules after TF-mocking tests.

Some test files inject MagicMock into sys.modules["tensorflow"] at import
time. This hook ensures the original state is restored between test modules
so that HAS_TF checks in other test files remain accurate.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Save original tensorflow-related modules before any test file can inject mocks
# ---------------------------------------------------------------------------
_ORIG_TF_MODULES: dict[str, object] = {}
for _key in list(sys.modules):
    if _key == "tensorflow" or _key.startswith("tensorflow."):
        _ORIG_TF_MODULES[_key] = sys.modules[_key]


def pytest_runtest_teardown(item: object) -> None:
    """After each test, remove any MagicMock-based tensorflow entries."""
    for key in list(sys.modules):
        if key == "tensorflow" or key.startswith("tensorflow."):
            mod = sys.modules[key]
            if hasattr(mod, "__class__") and "MagicMock" in type(mod).__name__:
                if key in _ORIG_TF_MODULES:
                    sys.modules[key] = _ORIG_TF_MODULES[key]
                else:
                    del sys.modules[key]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rng():
    """Deterministic NumPy random generator."""
    return np.random.default_rng(42)


@pytest.fixture
def sample_image():
    """128x128x11 float32 image simulating 11-channel satellite data."""
    return np.random.default_rng(0).random((128, 128, 11), dtype=np.float32)


@pytest.fixture
def sample_mask():
    """128x128 uint8 binary mask."""
    return np.random.default_rng(1).integers(0, 2, (128, 128)).astype(np.uint8)
