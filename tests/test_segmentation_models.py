# -*- coding: utf-8 -*-
"""Tests for src/segmentation_models.py."""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Mock TensorFlow before importing the module
# ---------------------------------------------------------------------------
mock_tf = MagicMock()
sys.modules["tensorflow"] = mock_tf
sys.modules["tensorflow.keras"] = mock_tf.keras
sys.modules["tensorflow.keras.applications"] = mock_tf.keras.applications
sys.modules["tensorflow.keras.layers"] = mock_tf.keras.layers

from src.segmentation_models import (
    SEGMENTATION_MODELS,
    build_model_by_name,
    count_parameters,
    estimate_model_complexity,
    get_model_info,
    list_segmentation_models,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_model():
    """Mock Keras Model with count_params and trainable_weights."""
    model = MagicMock()
    model.count_params.return_value = 2_000_000

    w1 = MagicMock()
    w1.numpy.return_value = np.zeros((64, 64, 3, 32))
    w2 = MagicMock()
    w2.numpy.return_value = np.zeros((32,))
    model.trainable_weights = [w1, w2]

    w_all = MagicMock()
    w_all.shape.num_elements.return_value = 36_896
    w_all2 = MagicMock()
    w_all2.shape.num_elements.return_value = 32
    model.weights = [w_all, w_all2]

    return model


@pytest.fixture
def sample_input_shape():
    return (256, 256, 11)


# ---------------------------------------------------------------------------
# list_segmentation_models tests
# ---------------------------------------------------------------------------

class TestListSegmentationModels:
    def test_returns_sorted_list_of_seven(self):
        models = list_segmentation_models()
        assert isinstance(models, list)
        assert len(models) == 7
        assert models == sorted(models)

    def test_contains_expected_names(self):
        models = list_segmentation_models()
        expected = {"attention_fpn", "deeplabv3", "fcn", "hrnet", "linknet", "pspnet", "segnet"}
        assert set(models) == expected


# ---------------------------------------------------------------------------
# get_model_info tests
# ---------------------------------------------------------------------------

class TestGetModelInfo:
    @pytest.mark.parametrize("name", [
        "fcn", "deeplabv3", "pspnet", "linknet", "segnet", "attention_fpn", "hrnet",
    ])
    def test_returns_valid_metadata(self, name):
        info = get_model_info(name)
        assert "name" in info
        assert "description" in info
        assert "complexity" in info
        assert "param_count_estimate" in info
        assert "recommended_input_size" in info
        assert info["name"] == name

    def test_complexity_values(self):
        for name in list_segmentation_models():
            info = get_model_info(name)
            assert info["complexity"] in ("low", "medium", "high")

    def test_raises_on_unknown_model(self):
        with pytest.raises(ValueError, match="Unknown model"):
            get_model_info("nonexistent_model")

    def test_case_insensitive(self):
        info = get_model_info("FCN")
        assert info["name"] == "fcn"


# ---------------------------------------------------------------------------
# count_parameters tests
# ---------------------------------------------------------------------------

class TestCountParameters:
    def test_returns_valid_counts(self, mock_model):
        result = count_parameters(mock_model)
        assert "total" in result
        assert "trainable" in result
        assert "non_trainable" in result
        assert result["total"] >= 0
        assert result["trainable"] >= 0
        assert result["non_trainable"] == result["total"] - result["trainable"]

    def test_total_equals_sum(self, mock_model):
        result = count_parameters(mock_model)
        assert result["total"] == result["trainable"] + result["non_trainable"]


# ---------------------------------------------------------------------------
# estimate_model_complexity tests
# ---------------------------------------------------------------------------

class TestEstimateModelComplexity:
    @pytest.mark.parametrize("name", [
        "fcn", "deeplabv3", "pspnet", "linknet", "segnet", "attention_fpn", "hrnet",
    ])
    def test_returns_valid_data(self, name):
        result = estimate_model_complexity(name)
        assert "model" in result
        assert "flops_estimate_gflops" in result
        assert "memory_estimate_mb" in result
        assert "inference_time_estimate_ms" in result
        assert result["model"] == name
        assert result["flops_estimate_gflops"] > 0
        assert result["memory_estimate_mb"] > 0
        assert result["inference_time_estimate_ms"] > 0

    def test_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unknown model"):
            estimate_model_complexity("nonexistent")

    def test_complexity_ordering(self):
        segnet = estimate_model_complexity("segnet")
        deeplab = estimate_model_complexity("deeplabv3")
        # DeepLabV3 should be more complex than SegNet per the FLOPS table
        assert deeplab["flops_estimate_gflops"] > segnet["flops_estimate_gflops"]


# ---------------------------------------------------------------------------
# build_model_by_name dispatch tests
# ---------------------------------------------------------------------------

class TestBuildModelByName:
    def test_dispatches_correctly(self):
        expected = MagicMock()
        fake_builder = MagicMock(return_value=expected)
        with patch.dict(SEGMENTATION_MODELS, {"fcn": fake_builder}):
            result = build_model_by_name("fcn", input_shape=(256, 256, 11), num_classes=1)
        fake_builder.assert_called_once()
        assert result is expected

    def test_raises_on_unknown_model(self, sample_input_shape):
        with pytest.raises(ValueError, match="Unknown model"):
            build_model_by_name("nonexistent_model", input_shape=sample_input_shape)

    def test_case_insensitive(self):
        expected = MagicMock()
        fake_builder = MagicMock(return_value=expected)
        with patch.dict(SEGMENTATION_MODELS, {"fcn": fake_builder}):
            result = build_model_by_name("FCN", input_shape=(256, 256, 11))
        fake_builder.assert_called_once()
        assert result is expected


# ---------------------------------------------------------------------------
# All model builders exist in SEGMENTATION_MODELS registry
# ---------------------------------------------------------------------------

class TestRegistryCompleteness:
    def test_all_seven_builders_registered(self):
        expected_builders = {
            "fcn", "deeplabv3", "pspnet", "linknet",
            "segnet", "attention_fpn", "hrnet",
        }
        assert set(SEGMENTATION_MODELS.keys()) == expected_builders

    @pytest.mark.parametrize("name", [
        "fcn", "deeplabv3", "pspnet", "linknet", "segnet", "attention_fpn", "hrnet",
    ])
    def test_builder_is_callable(self, name):
        assert callable(SEGMENTATION_MODELS[name])

    def test_registry_keys_match_list_function(self):
        assert sorted(SEGMENTATION_MODELS.keys()) == list_segmentation_models()

    def test_registry_keys_match_model_info(self):
        for name in SEGMENTATION_MODELS:
            info = get_model_info(name)
            assert info["name"] == name
