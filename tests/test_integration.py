"""Integration tests for end-to-end segmentation pipeline."""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))


@pytest.fixture
def synthetic_image(tmp_path):
    """Create a synthetic 11-channel GeoTIFF for testing."""
    try:
        import rasterio
        from rasterio.transform import from_bounds

        img_path = tmp_path / "test_image.tif"
        data = np.random.default_rng(42).random((11, 256, 256), dtype=np.float32)
        transform = from_bounds(76.5, 42.8, 77.5, 43.2, 256, 256)

        with rasterio.open(
            img_path, "w", driver="GTiff",
            height=256, width=256, count=11,
            dtype="float32", crs="EPSG:32642",
            transform=transform,
        ) as dst:
            dst.write(data)
        return img_path
    except ImportError:
        pytest.skip("rasterio not installed")


class TestSegmentationService:
    """Tests for segmentation_service module functions."""

    def test_calc_area_default_pixel_size(self):
        from app.services.segmentation_service import DEFAULT_PIXEL_SIZE_M, _calc_area
        mask = np.ones((100, 100), dtype=np.float32)
        area = _calc_area(mask)
        expected = 100 * 100 * (DEFAULT_PIXEL_SIZE_M ** 2) / 1e6
        assert abs(area - round(expected, 4)) < 1e-6

    def test_calc_area_custom_pixel_size(self):
        from app.services.segmentation_service import _calc_area
        mask = np.ones((100, 100), dtype=np.float32)
        area = _calc_area(mask, pixel_area_m2=400.0)
        expected = 100 * 100 * 400 / 1e6
        assert abs(area - round(expected, 4)) < 1e-6

    def test_calc_area_empty_mask(self):
        from app.services.segmentation_service import _calc_area
        mask = np.zeros((256, 256), dtype=np.float32)
        area = _calc_area(mask)
        assert area == 0.0

    def test_run_ndsi_basic(self):
        from app.services.segmentation_service import _run_ndsi
        image = np.random.default_rng(0).random((256, 256, 11), dtype=np.float32)
        mask = _run_ndsi(image, threshold=0.4)
        assert mask.shape == (256, 256)
        assert mask.dtype == np.float32
        assert set(np.unique(mask)).issubset({0.0, 1.0})

    def test_run_ndsi_high_threshold_fewer_pixels(self):
        from app.services.segmentation_service import _run_ndsi
        image = np.random.default_rng(0).random((256, 256, 11), dtype=np.float32)
        mask_low = _run_ndsi(image, threshold=0.3)
        mask_high = _run_ndsi(image, threshold=0.6)
        assert mask_high.sum() <= mask_low.sum()

    def test_ensure_11_channels_from_11(self):
        from app.services.segmentation_service import _ensure_11_channels
        img = np.random.default_rng(0).random((64, 64, 11), dtype=np.float32)
        result = _ensure_11_channels(img)
        assert result.shape[-1] == 11

    def test_ensure_11_channels_from_7(self):
        from app.services.segmentation_service import _ensure_11_channels
        img = np.random.default_rng(0).random((64, 64, 7), dtype=np.float32)
        result = _ensure_11_channels(img)
        assert result.shape[-1] == 11

    def test_ensure_11_channels_wrong_count_raises(self):
        from app.services.segmentation_service import _ensure_11_channels
        img = np.random.default_rng(0).random((64, 64, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="11-band"):
            _ensure_11_channels(img)

    def test_save_mask_creates_file(self, tmp_path):
        from app.services.segmentation_service import _save_mask
        with patch("app.services.segmentation_service.RESULTS_DIR", tmp_path):
            mask = np.random.default_rng(0).random((64, 64))
            path = _save_mask(mask, "test_mask")
            assert path.exists()
            assert path.suffix == ".png"
