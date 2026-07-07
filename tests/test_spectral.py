"""Tests for src/spectral.py spectral index utilities."""

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestSpectralRegistry:
    def test_list_indices_includes_core(self):
        from src.spectral import list_indices

        names = list_indices()
        assert "ndvi" in names
        assert "ndsi" in names
        assert "ndwi" in names

    def test_get_index_info_ndvi(self):
        from src.spectral import get_index_info

        info = get_index_info("ndvi")
        assert info["name"]
        assert "bands" in info

    def test_get_index_info_unknown_raises(self):
        from src.spectral import get_index_info

        with pytest.raises(KeyError):
            get_index_info("not_a_real_index")


class TestSpectralCompute:
    @pytest.fixture
    def bands(self):
        shape = (4, 4)
        return {
            "green": np.full(shape, 0.2, dtype=np.float32),
            "red": np.full(shape, 0.1, dtype=np.float32),
            "nir": np.full(shape, 0.5, dtype=np.float32),
            "swir1": np.full(shape, 0.05, dtype=np.float32),
        }

    def test_compute_ndvi(self, bands):
        from src.spectral import compute_ndvi

        ndvi = compute_ndvi(bands)
        assert ndvi.shape == bands["red"].shape
        assert float(np.mean(ndvi)) > 0.5

    def test_compute_index_ndsi(self, bands):
        from src.spectral import compute_index

        ndsi = compute_index("ndsi", bands)
        assert ndsi.shape == bands["green"].shape
        assert -1.0 <= float(np.mean(ndsi)) <= 1.0

    def test_compute_index_unknown_raises(self, bands):
        from src.spectral import compute_index

        with pytest.raises(KeyError):
            compute_index("fake_index", bands)
