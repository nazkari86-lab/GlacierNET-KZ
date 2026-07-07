"""Tests for src/models.py model registry functions."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestModelRegistry:
    """Tests for list_models, build_model_by_name, get_model_info."""

    def test_list_models_returns_list(self):
        from src.models import list_models
        result = list_models()
        assert isinstance(result, list)

    def test_list_models_contains_unet(self):
        from src.models import list_models
        result = list_models()
        assert "unet" in result

    def test_list_models_contains_attention_unet(self):
        from src.models import list_models
        result = list_models()
        assert "attention_unet" in result

    def test_list_models_contains_unet_plus_plus(self):
        from src.models import list_models
        result = list_models()
        assert "unet_plus_plus" in result

    def test_get_model_info_unet(self):
        from src.models import get_model_info
        info = get_model_info("unet")
        assert info["name"] == "unet"
        assert "builder" in info
        assert "doc" in info

    def test_get_model_info_attention_unet(self):
        from src.models import get_model_info
        info = get_model_info("attention_unet")
        assert info["name"] == "attention_unet"

    def test_get_model_info_unet_plus_plus(self):
        from src.models import get_model_info
        info = get_model_info("unet_plus_plus")
        assert info["name"] == "unet_plus_plus"

    def test_get_model_info_unknown_raises(self):
        from src.models import get_model_info
        with pytest.raises(ValueError, match="Unknown model"):
            get_model_info("nonexistent_model")

    def test_build_model_by_name_unknown_raises(self):
        from src.models import build_model_by_name
        with pytest.raises(ValueError, match="Unknown model"):
            build_model_by_name("nonexistent_model", (256, 256, 11))

    def test_model_registry_has_builder(self):
        from src.models import get_model_info, list_models
        for name in list_models():
            info = get_model_info(name)
            assert isinstance(info["builder"], str), f"{name} builder not a string"
