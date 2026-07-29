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

    @patch("app.services.model_availability.verify_trusted_model", return_value="digest")
    @patch("app.services.model_availability.weights_path")
    def test_ensemble_requires_unet_weights(self, mock_wp, _mock_verify):
        from app.services.model_availability import is_model_available

        unet = Path("/models/unet_best.h5")
        missing = Path("/models/missing.h5")

        mock_wp.side_effect = lambda name: unet if name == "unet" else missing

        with patch("pathlib.Path.exists", return_value=True):
            assert is_model_available("ensemble") is True

        with patch("pathlib.Path.exists", return_value=False):
            assert is_model_available("ensemble") is False

    def test_deployable_temporal_models_publish_feature_contract(self):
        from app.services.model_availability import filter_available_models

        catalog = [{"name": "temporal_s2_terrain_s1", "display_name": "Multimodal"}]
        result = filter_available_models(catalog)
        assert result[0]["available"] is True
        assert result[0]["channel_count"] == 16
        assert result[0]["feature_schema"][-2:] == ["VV_dB_normalized", "VH_dB_normalized"]
        assert result[0]["decision_threshold"] == pytest.approx(0.5)
        assert result[0]["recommended"] is True
