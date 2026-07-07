"""Tests for model availability checks."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestModelAvailability:
    def test_ndsi_always_available(self):
        from app.services.model_availability import is_model_available

        assert is_model_available("ndsi") is True

    @patch("app.services.model_availability.weights_path")
    def test_keras_model_missing_weights(self, mock_path):
        mock_path.return_value = Path("/nonexistent/unet_best.h5")

        from app.services.model_availability import is_model_available

        assert is_model_available("unet") is False

    @patch("app.services.model_availability.is_model_available")
    def test_filter_catalog(self, mock_available):
        mock_available.side_effect = lambda name: name in ("unet", "ndsi")

        from app.services.model_availability import filter_available_models

        catalog = [
            {"name": "unet", "display_name": "U-Net"},
            {"name": "attention_unet", "display_name": "Attention U-Net"},
            {"name": "ndsi", "display_name": "NDSI"},
        ]
        result = filter_available_models(catalog)
        assert len(result) == 2
        assert result[0]["available"] is True

    @patch("app.services.model_availability.weights_path")
    def test_ensemble_requires_unet_weights(self, mock_wp):
        from app.services.model_availability import is_model_available

        unet = Path("/models/unet_best.h5")
        missing = Path("/models/missing.h5")

        mock_wp.side_effect = lambda name: unet if name == "unet" else missing

        with patch("pathlib.Path.exists", return_value=True):
            assert is_model_available("ensemble") is True

        with patch("pathlib.Path.exists", return_value=False):
            assert is_model_available("ensemble") is False
