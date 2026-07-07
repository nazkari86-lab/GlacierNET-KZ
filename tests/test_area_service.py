"""Tests for app/services/area_service.py — unit tests (no file I/O)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.metrics import pixels_to_area_km2


class TestCalcAreaFromMaskPIL:
    """Test the non-TIF path (PIL image)."""

    @patch("app.services.area_service.Path")
    @patch("app.services.area_service.Image")
    def test_pure_white_mask(self, mock_image_class, mock_path_class):
        """All pixels > 127 -> all counted as glacier."""
        mock_path_instance = MagicMock()
        mock_path_instance.suffix = ".png"
        mock_path_class.return_value = mock_path_instance

        mask_array = np.full((100, 100), 255, dtype=np.uint8)
        mock_pil_image = MagicMock()
        mock_pil_image.convert.return_value = mock_pil_image
        mock_pil_image.__array__ = MagicMock(return_value=mask_array)
        mock_image_class.open.return_value = mock_pil_image

        import app.services.area_service as svc

        with patch("app.services.area_service.np.array", return_value=mask_array):
            result = svc.calc_area_from_mask("fake.png", pixel_size_m=10.0)

        assert result["pixel_count"] == 10000
        expected_area = 10000 * 100 / 1e6  # 1.0 km^2
        assert result["area_km2"] == round(expected_area, 4)

    def test_pixels_to_area_known(self):
        """Direct unit test for the underlying metric."""
        # 50 pixels * 100 m^2 = 5000 m^2 = 0.005 km^2
        assert pixels_to_area_km2(50, 100.0) == pytest.approx(0.005)

    def test_zero_pixels(self):
        assert pixels_to_area_km2(0, 100.0) == 0.0
