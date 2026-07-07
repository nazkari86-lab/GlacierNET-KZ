"""Tests for predict.py — pure functions that don't need TF/sklearn models."""

import numpy as np

from predict import run_ndsi


class TestRunNDSI:
    def test_basic_shape(self, sample_image):
        result = run_ndsi(sample_image)
        assert result.shape == sample_image.shape[:2]
        assert result.dtype == np.uint8

    def test_binary_output(self, sample_image):
        result = run_ndsi(sample_image)
        unique = set(np.unique(result))
        assert unique.issubset({0, 1})

    def test_custom_threshold(self, sample_image):
        low = run_ndsi(sample_image, threshold=0.1)
        high = run_ndsi(sample_image, threshold=0.9)
        # Higher threshold -> less glacier pixels
        assert low.sum() >= high.sum()

    def test_deterministic(self, sample_image):
        r1 = run_ndsi(sample_image)
        r2 = run_ndsi(sample_image)
        np.testing.assert_array_equal(r1, r2)

    def test_11_channels_uses_precomputed_ndsi(self, sample_image):
        """NDSI is at band index 7 (pre-computed), not raw green/SWIR bands."""
        img = np.zeros((64, 64, 11), dtype=np.float32)
        img[:, :, 7] = 0.8  # NDSI (pre-computed, high)
        result = run_ndsi(img, threshold=0.4)
        assert result.mean() == 1.0

        img2 = np.zeros((64, 64, 11), dtype=np.float32)
        img2[:, :, 7] = 0.1  # NDSI (pre-computed, low)
        result2 = run_ndsi(img2, threshold=0.4)
        assert result2.mean() == 0.0
