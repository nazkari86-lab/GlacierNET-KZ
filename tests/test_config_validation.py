"""Tests for src/config.py validate_config() and related functions."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestValidateConfig:
    """Tests for validate_config()."""

    def test_valid_config(self):
        from src.config import validate_config
        errors = validate_config()
        assert errors == []

    def test_invalid_model_name(self):
        import src.config as cfg
        original = cfg.MODEL_NAME
        try:
            cfg.MODEL_NAME = "nonexistent_model"
            errors = cfg.validate_config()
            assert any("MODEL_NAME" in e for e in errors)
        finally:
            cfg.MODEL_NAME = original

    def test_splits_sum_not_one(self):
        import src.config as cfg
        orig_train = cfg.TRAIN_FRACTION
        orig_val = cfg.VAL_FRACTION
        orig_test = cfg.TEST_FRACTION
        try:
            cfg.TRAIN_FRACTION = 0.5
            cfg.VAL_FRACTION = 0.3
            cfg.TEST_FRACTION = 0.3
            errors = cfg.validate_config()
            assert any("1.0" in e for e in errors)
        finally:
            cfg.TRAIN_FRACTION = orig_train
            cfg.VAL_FRACTION = orig_val
            cfg.TEST_FRACTION = orig_test

    def test_batch_size_zero(self):
        import src.config as cfg
        original = cfg.BATCH_SIZE
        try:
            cfg.BATCH_SIZE = 0
            errors = cfg.validate_config()
            assert any("BATCH_SIZE" in e for e in errors)
        finally:
            cfg.BATCH_SIZE = original

    def test_learning_rate_zero(self):
        import src.config as cfg
        original = cfg.LEARNING_RATE
        try:
            cfg.LEARNING_RATE = 0.0
            errors = cfg.validate_config()
            assert any("LEARNING_RATE" in e for e in errors)
        finally:
            cfg.LEARNING_RATE = original

    def test_learning_rate_too_large(self):
        import src.config as cfg
        original = cfg.LEARNING_RATE
        try:
            cfg.LEARNING_RATE = 1.5
            errors = cfg.validate_config()
            assert any("LEARNING_RATE" in e for e in errors)
        finally:
            cfg.LEARNING_RATE = original

    def test_patch_size_too_small(self):
        import src.config as cfg
        original = cfg.PATCH_SIZE
        try:
            cfg.PATCH_SIZE = 16
            errors = cfg.validate_config()
            assert any("PATCH_SIZE" in e for e in errors)
        finally:
            cfg.PATCH_SIZE = original

    def test_empty_unet_filters(self):
        import src.config as cfg
        original = cfg.UNET_FILTERS
        try:
            cfg.UNET_FILTERS = []
            errors = cfg.validate_config()
            assert any("UNET_FILTERS" in e for e in errors)
        finally:
            cfg.UNET_FILTERS = original

    def test_invalid_year_range(self):
        import src.config as cfg
        original = cfg.YEARS_SENTINEL2
        try:
            cfg.YEARS_SENTINEL2 = [1980, 2020]
            errors = cfg.validate_config()
            assert any("YEARS_SENTINEL2" in e for e in errors)
        finally:
            cfg.YEARS_SENTINEL2 = original

    def test_valid_model_names(self):
        import src.config as cfg
        for name in ["unet", "attention_unet", "unet_plus_plus"]:
            original = cfg.MODEL_NAME
            cfg.MODEL_NAME = name
            errors = cfg.validate_config()
            assert errors == [], f"Model {name} should be valid"
            cfg.MODEL_NAME = original

    def test_n_channels_mismatch(self):
        import src.config as cfg
        original = cfg.N_CHANNELS
        try:
            cfg.N_CHANNELS = 99
            errors = cfg.validate_config()
            assert any("N_CHANNELS" in e for e in errors)
        finally:
            cfg.N_CHANNELS = original
