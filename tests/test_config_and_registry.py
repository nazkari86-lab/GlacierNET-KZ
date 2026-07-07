"""Tests for src/config.py (validate_config) and src/models.py (registry)."""

import sys

import pytest


def _has_real_tf() -> bool:
    """Check if real TensorFlow is available (not a MagicMock stub)."""
    mod = sys.modules.get("tensorflow")
    if mod is None:
        try:
            import importlib
            importlib.import_module("tensorflow")
            mod = sys.modules.get("tensorflow")
        except ImportError:
            return False
    if mod is None:
        return False
    # Reject MagicMock stubs injected by other test modules
    if hasattr(mod, "__class__") and "MagicMock" in type(mod).__name__:
        return False
    return True


class TestValidateConfig:
    def test_valid_config_returns_no_errors(self):
        from src.config import validate_config

        errors = validate_config()
        assert errors == []

    def test_invalid_model_name_returns_error(self):
        import src.config as cfg

        original = cfg.MODEL_NAME
        try:
            cfg.MODEL_NAME = "nonexistent_model"
            errors = cfg.validate_config()
            assert any("nonexistent_model" in e for e in errors)
        finally:
            cfg.MODEL_NAME = original

    def test_split_sum_not_one_returns_error(self):
        import src.config as cfg

        orig_train = cfg.TRAIN_FRACTION
        try:
            cfg.TRAIN_FRACTION = 0.5
            errors = cfg.validate_config()
            assert any("Сумма долей" in e for e in errors)
        finally:
            cfg.TRAIN_FRACTION = orig_train

    def test_patch_size_too_small_returns_error(self):
        import src.config as cfg

        orig = cfg.PATCH_SIZE
        try:
            cfg.PATCH_SIZE = 10
            errors = cfg.validate_config()
            assert any("PATCH_SIZE" in e for e in errors)
        finally:
            cfg.PATCH_SIZE = orig

    def test_n_channels_mismatch_returns_error(self):
        import src.config as cfg

        orig = cfg.N_CHANNELS
        try:
            cfg.N_CHANNELS = 999
            errors = cfg.validate_config()
            assert any("N_CHANNELS" in e for e in errors)
        finally:
            cfg.N_CHANNELS = orig


class TestModelRegistry:
    def test_list_models_returns_three(self):
        from src.models import list_models

        names = list_models()
        assert "unet" in names
        assert "attention_unet" in names
        assert "unet_plus_plus" in names
        assert len(names) == 3

    def test_get_model_info_valid(self):
        from src.models import get_model_info

        info = get_model_info("unet")
        assert info["name"] == "unet"
        assert info["builder"] == "build_unet"

    def test_get_model_info_invalid_raises(self):
        from src.models import get_model_info

        with pytest.raises(ValueError, match="Unknown model"):
            get_model_info("nonexistent")

    def test_build_model_by_name_invalid_raises(self):
        from src.models import build_model_by_name

        with pytest.raises(ValueError, match="Unknown model"):
            build_model_by_name("nonexistent")

    def test_build_model_by_name_unet(self):
        if not _has_real_tf():
            pytest.skip("TensorFlow not installed")
        from src.models import build_model_by_name

        model = build_model_by_name("unet", input_shape=(64, 64, 11))
        assert model.name == "U-Net"
        assert model.output_shape == (None, 64, 64, 1)

    def test_build_model_by_name_unet_plus_plus(self):
        if not _has_real_tf():
            pytest.skip("TensorFlow not installed")
        from src.models import build_model_by_name

        model = build_model_by_name("unet_plus_plus", input_shape=(64, 64, 11))
        assert model.name == "unet_plus_plus"
        assert model.output_shape == (None, 64, 64, 1)

    def test_build_model_by_name_attention_unet(self):
        if not _has_real_tf():
            pytest.skip("TensorFlow not installed")
        from src.models import build_model_by_name

        model = build_model_by_name("attention_unet", input_shape=(64, 64, 11))
        assert model.name == "Attention-U-Net"
        assert model.output_shape == (None, 64, 64, 1)
