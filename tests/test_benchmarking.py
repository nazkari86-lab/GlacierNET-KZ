# -*- coding: utf-8 -*-
"""Tests for src/benchmarking.py."""

import os
import sys
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Mock TensorFlow before importing any src module
# ---------------------------------------------------------------------------
_mock_tf = MagicMock()
sys.modules["tensorflow"] = _mock_tf
sys.modules["tensorflow.keras"] = _mock_tf.keras
sys.modules["tensorflow.keras.applications"] = _mock_tf.keras.applications
sys.modules["tensorflow.keras.layers"] = _mock_tf.keras.layers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.benchmarking import (
    benchmark_inference,
    benchmark_throughput,
    compare_benchmarks,
    estimate_model_size,
    generate_benchmark_report,
    load_benchmark_results,
    measure_latency,
    save_benchmark_results,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_model():
    """Mock model with a .predict method that returns random output."""
    model = MagicMock()
    model.predict.side_effect = lambda x, **kw: np.random.randn(*x.shape)
    model.count_params.return_value = 1_000_000
    model.weights = []
    return model


@pytest.fixture
def sample_image():
    """Single 256x256x3 image."""
    return np.random.randn(256, 256, 3).astype(np.float32)


@pytest.fixture
def sample_images():
    """List of 4 images."""
    return [np.random.randn(256, 256, 3).astype(np.float32) for _ in range(4)]


@pytest.fixture
def inference_result():
    """Pre-computed inference benchmark result dict."""
    return {
        "mean_s": 0.05,
        "std_s": 0.005,
        "min_s": 0.04,
        "max_s": 0.07,
        "p50_s": 0.05,
        "p95_s": 0.06,
        "p99_s": 0.07,
        "median_s": 0.05,
        "peak_memory_mb": 128.0,
        "throughput_fps": 20.0,
        "total_time_s": 5.0,
        "n_runs": 100,
    }


# ---------------------------------------------------------------------------
# benchmark_inference tests
# ---------------------------------------------------------------------------

class TestBenchmarkInference:
    def test_returns_expected_keys(self, mock_model, sample_image):
        result = benchmark_inference(
            mock_model, sample_image, n_runs=5, warmup=1, model_name="test"
        )
        expected_keys = {
            "mean_s", "std_s", "min_s", "max_s", "p50_s", "p95_s", "p99_s",
            "median_s", "peak_memory_mb", "throughput_fps", "total_time_s", "n_runs",
        }
        assert expected_keys <= set(result.keys())

    def test_valid_timing_values(self, mock_model, sample_image):
        result = benchmark_inference(
            mock_model, sample_image, n_runs=5, warmup=1
        )
        assert result["min_s"] <= result["mean_s"] <= result["max_s"]
        assert result["p50_s"] <= result["p95_s"] <= result["p99_s"]
        assert result["n_runs"] == 5
        assert result["throughput_fps"] >= 0

    def test_caches_result(self, mock_model, sample_image):
        benchmark_inference(mock_model, sample_image, n_runs=3, warmup=1, model_name="cached")
        from src.benchmarking import BENCHMARK_CACHE
        assert any("cached" in k for k in BENCHMARK_CACHE)


# ---------------------------------------------------------------------------
# benchmark_throughput tests
# ---------------------------------------------------------------------------

class TestBenchmarkThroughput:
    def test_covers_all_batch_sizes(self, mock_model, sample_images):
        result = benchmark_throughput(
            mock_model, sample_images, n_runs=3, model_name="tp_test"
        )
        # Only batch sizes <= len(images) are tested
        for bs in [1, 2, 4]:
            assert str(bs) in result

    def test_skips_large_batch_sizes(self, mock_model, sample_images):
        result = benchmark_throughput(
            mock_model, sample_images, n_runs=3
        )
        # 8, 16, 32 exceed len(images)=4
        assert "8" not in result
        assert "16" not in result
        assert "32" not in result

    def test_batch_result_has_expected_keys(self, mock_model, sample_images):
        result = benchmark_throughput(
            mock_model, sample_images, n_runs=3, model_name="tp"
        )
        for bs_str, data in result.items():
            assert data["batch_size"] == int(bs_str)
            assert "mean_s" in data
            assert "images_per_s" in data
            assert "ms_per_image" in data


# ---------------------------------------------------------------------------
# measure_latency tests
# ---------------------------------------------------------------------------

class TestMeasureLatency:
    def test_returns_valid_percentiles(self, mock_model, sample_image):
        result = measure_latency(
            mock_model, sample_image, n_runs=50, warmup=5, model_name="lat"
        )
        assert "p50_ms" in result
        assert "p95_ms" in result
        assert "p99_ms" in result
        assert "p999_ms" in result
        assert result["p50_ms"] <= result["p95_ms"] <= result["p99_ms"] <= result["p999_ms"]
        assert result["n_runs"] == 50

    def test_mean_in_range(self, mock_model, sample_image):
        result = measure_latency(
            mock_model, sample_image, n_runs=20, warmup=2
        )
        assert result["min_ms"] <= result["mean_ms"] <= result["max_ms"]


# ---------------------------------------------------------------------------
# compare_benchmarks tests
# ---------------------------------------------------------------------------

class TestCompareBenchmarks:
    def test_returns_dataframe(self, mock_model, sample_image):
        df = compare_benchmarks(
            [mock_model, mock_model], sample_image, names=["A", "B"], n_runs=5
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "model" in df.columns

    def test_default_names(self, mock_model, sample_image):
        df = compare_benchmarks([mock_model], sample_image, n_runs=5)
        assert df.iloc[0]["model"] == "Model 1"


# ---------------------------------------------------------------------------
# estimate_model_size tests
# ---------------------------------------------------------------------------

class TestEstimateModelSize:
    def test_returns_valid_counts(self, mock_model):
        result = estimate_model_size(mock_model)
        assert "param_count" in result
        assert "weight_file_size_mb" in result
        assert "total_memory_mb" in result
        assert result["param_count"] >= 0
        assert result["weight_file_size_mb"] >= 0

    def test_model_with_weights(self):
        model = MagicMock()
        model.count_params.return_value = 500_000
        w1 = MagicMock()
        w1.shape = (100, 100)  # np.prod = 10,000 < 500,000 so max() stays at count_params
        model.weights = [w1]
        model.output_shape = (None, 256, 256, 1)
        result = estimate_model_size(model)
        assert result["param_count"] == 500_000


# ---------------------------------------------------------------------------
# generate_benchmark_report tests
# ---------------------------------------------------------------------------

class TestGenerateBenchmarkReport:
    def test_produces_markdown_string(self, inference_result):
        report = generate_benchmark_report(inference_result)
        assert isinstance(report, str)
        assert "# GlacierNET-KZ Benchmark Report" in report
        assert "## Inference Timing" in report
        assert "Mean" in report

    def test_latency_section(self):
        results = {"p50_ms": 5.0, "p95_ms": 10.0, "p99_ms": 20.0, "p999_ms": 50.0, "mean_ms": 7.5}
        report = generate_benchmark_report(results)
        assert "## Latency Distribution" in report

    def test_model_size_section(self):
        results = {"param_count": 1_000_000, "weight_file_size_mb": 4.0, "activation_memory_mb": 2.0, "total_memory_mb": 6.0}
        report = generate_benchmark_report(results)
        assert "## Model Size" in report

    def test_empty_results(self):
        report = generate_benchmark_report({})
        assert isinstance(report, str)
        assert "# GlacierNET-KZ Benchmark Report" in report
        # Empty dict produces header-only report (no data sections)
        assert "## Inference Timing" not in report


# ---------------------------------------------------------------------------
# JSON save/load roundtrip
# ---------------------------------------------------------------------------

class TestSaveLoadResults:
    def test_roundtrip(self, inference_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bench.json")
            save_benchmark_results(inference_result, path)
            assert os.path.exists(path)
            loaded = load_benchmark_results(path)
            assert loaded["mean_s"] == inference_result["mean_s"]
            assert loaded["n_runs"] == inference_result["n_runs"]

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "a", "b", "c", "bench.json")
            save_benchmark_results({"test": 1}, path)
            assert os.path.exists(path)

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_benchmark_results("/nonexistent/path.json")
