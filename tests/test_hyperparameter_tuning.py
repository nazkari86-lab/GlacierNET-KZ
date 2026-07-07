# -*- coding: utf-8 -*-
"""Tests for src/hyperparameter_tuning.py."""

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

from src.hyperparameter_tuning import (
    SearchSpace,
    build_optimizer,
    compute_search_summary,
    get_best_params,
    grid_search,
    list_optimizers,
    load_search_results,
    prune_dominated_configs,
    random_search,
    save_search_results,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def search_space():
    """Default SearchSpace for testing."""
    return SearchSpace(
        learning_rate=(1e-5, 1e-2),
        batch_size=[8, 16, 32],
        dropout_rate=(0.0, 0.5),
        optimizer=["adam", "sgd"],
        augmentation=True,
        weight_decay=(1e-6, 1e-3),
        epochs=(10, 30),
    )


@pytest.fixture
def small_grid():
    """Small parameter grid for fast tests."""
    return {
        "learning_rate": [1e-4, 1e-3],
        "batch_size": [8, 16],
    }


@pytest.fixture
def dummy_train_fn():
    """Fake training function returning metric dict."""

    def _train(model, config):
        return {
            "val_iou": float(np.random.default_rng(42).uniform(0.5, 0.95)),
            "val_loss": float(np.random.default_rng(42).uniform(0.1, 0.5)),
        }

    return _train


@pytest.fixture
def dummy_model_builder():
    """Fake model builder that returns a callable stub."""

    def _build(config):
        class _Model:
            def __init__(self, cfg):
                self.cfg = cfg
        return _Model(config)

    return _build


@pytest.fixture
def sample_results_df():
    """DataFrame mimicking search results."""
    return pd.DataFrame({
        "cfg_learning_rate": [1e-4, 1e-3, 1e-5],
        "cfg_batch_size": [8, 16, 32],
        "cfg_optimizer": ["adam", "sgd", "adam"],
        "val_iou": [0.85, 0.72, 0.90],
        "val_loss": [0.25, 0.40, 0.18],
        "time_sec": [1.0, 0.8, 1.2],
        "status": ["success", "success", "success"],
    })


# ---------------------------------------------------------------------------
# SearchSpace tests
# ---------------------------------------------------------------------------

class TestSearchSpace:
    def test_to_grid_returns_all_keys(self, search_space):
        grid = search_space.to_grid(lr_levels=3, dropout_levels=3, wd_levels=3, epoch_levels=3)
        expected_keys = {"learning_rate", "batch_size", "dropout_rate", "optimizer", "weight_decay", "epochs", "augmentation"}
        assert set(grid.keys()) == expected_keys

    def test_to_grid_values_in_ranges(self, search_space):
        grid = search_space.to_grid(lr_levels=5, dropout_levels=5, wd_levels=5, epoch_levels=5)
        for lr in grid["learning_rate"]:
            assert 1e-5 <= lr <= 1e-2
        for do in grid["dropout_rate"]:
            assert 0.0 <= do <= 0.5
        for wd in grid["weight_decay"]:
            assert 1e-6 <= wd <= 1e-3

    def test_to_grid_no_augmentation_key_when_false(self):
        space = SearchSpace(augmentation=False)
        grid = space.to_grid()
        assert "augmentation" not in grid

    def test_sample_random_returns_all_keys(self, search_space):
        np.random.RandomState(0)
        sample = search_space.sample_random(rng=__import__("random").Random(42))
        assert set(sample.keys()) == {
            "learning_rate", "batch_size", "dropout_rate",
            "optimizer", "weight_decay", "epochs", "augmentation",
        }

    def test_sample_random_values_in_ranges(self, search_space):
        for _ in range(50):
            cfg = search_space.sample_random(rng=__import__("random").Random(42))
            assert 1e-5 <= cfg["learning_rate"] <= 1e-2
            assert cfg["batch_size"] in [8, 16, 32]
            assert 0.0 <= cfg["dropout_rate"] <= 0.5
            assert cfg["optimizer"] in ["adam", "sgd"]
            assert 1e-6 <= cfg["weight_decay"] <= 1e-3
            assert 10 <= cfg["epochs"] <= 30

    def test_sample_random_deterministic_with_seed(self, search_space):
        r1 = search_space.sample_random(rng=__import__("random").Random(99))
        r2 = search_space.sample_random(rng=__import__("random").Random(99))
        assert r1 == r2


# ---------------------------------------------------------------------------
# grid_search tests
# ---------------------------------------------------------------------------

class TestGridSearch:
    def test_returns_dataframe(self, small_grid, dummy_model_builder, dummy_train_fn):
        df = grid_search(small_grid, dummy_model_builder, dummy_train_fn)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4  # 2 * 2

    def test_all_combinations_present(self, small_grid, dummy_model_builder, dummy_train_fn):
        df = grid_search(small_grid, dummy_model_builder, dummy_train_fn)
        lrs = df["cfg_learning_rate"].tolist()
        bs = df["cfg_batch_size"].tolist()
        assert set(lrs) == {1e-4, 1e-3}
        assert set(bs) == {8, 16}

    def test_results_have_status_column(self, small_grid, dummy_model_builder, dummy_train_fn):
        df = grid_search(small_grid, dummy_model_builder, dummy_train_fn)
        assert "status" in df.columns
        assert all(s == "success" for s in df["status"])


# ---------------------------------------------------------------------------
# random_search tests
# ---------------------------------------------------------------------------

class TestRandomSearch:
    def test_returns_requested_count(self, dummy_model_builder, dummy_train_fn):
        space = {"learning_rate": (1e-5, 1e-2), "batch_size": [8, 16, 32]}
        df = random_search(space, dummy_model_builder, dummy_train_fn, n_iter=10, seed=42)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

    def test_reproducible_with_seed(self, dummy_model_builder, dummy_train_fn):
        space = {"learning_rate": (1e-5, 1e-2)}
        df1 = random_search(space, dummy_model_builder, dummy_train_fn, n_iter=5, seed=123)
        df2 = random_search(space, dummy_model_builder, dummy_train_fn, n_iter=5, seed=123)
        # time_sec is wall-clock time, so only compare config columns
        cfg_cols = [c for c in df1.columns if c.startswith("cfg_")]
        pd.testing.assert_frame_equal(df1[cfg_cols], df2[cfg_cols])

    def test_different_seeds_differ(self, dummy_model_builder, dummy_train_fn):
        space = {"learning_rate": (1e-5, 1e-2)}
        df1 = random_search(space, dummy_model_builder, dummy_train_fn, n_iter=5, seed=1)
        df2 = random_search(space, dummy_model_builder, dummy_train_fn, n_iter=5, seed=2)
        assert not df1["cfg_learning_rate"].equals(df2["cfg_learning_rate"])


# ---------------------------------------------------------------------------
# get_best_params tests
# ---------------------------------------------------------------------------

class TestGetBestParams:
    def test_returns_best_config_max(self, sample_results_df):
        best = get_best_params(sample_results_df, metric="val_iou", mode="max")
        assert best["learning_rate"] == 1e-5  # iou=0.90 is highest
        assert best["batch_size"] == 32

    def test_returns_best_config_min(self, sample_results_df):
        best = get_best_params(sample_results_df, metric="val_loss", mode="min")
        assert best["learning_rate"] == 1e-5  # loss=0.18 is lowest

    def test_raises_on_missing_metric(self, sample_results_df):
        with pytest.raises(KeyError, match="not found"):
            get_best_params(sample_results_df, metric="nonexistent")

    def test_raises_on_invalid_mode(self, sample_results_df):
        with pytest.raises(ValueError, match="mode must be"):
            get_best_params(sample_results_df, metric="val_iou", mode="median")

    def test_empty_on_all_nan(self):
        df = pd.DataFrame({"cfg_x": [1], "val_iou": [float("nan")]})
        best = get_best_params(df, metric="val_iou")
        assert best == {}


# ---------------------------------------------------------------------------
# compute_search_summary tests
# ---------------------------------------------------------------------------

class TestComputeSearchSummary:
    def test_summary_has_expected_keys(self, sample_results_df):
        summary = compute_search_summary(sample_results_df)
        assert "val_iou" in summary
        assert "mean" in summary["val_iou"]
        assert "std" in summary["val_iou"]
        assert "min" in summary["val_iou"]
        assert "max" in summary["val_iou"]

    def test_summary_excludes_config_columns(self, sample_results_df):
        summary = compute_search_summary(sample_results_df)
        for key in summary:
            assert not key.startswith("cfg_")


# ---------------------------------------------------------------------------
# Optimizer registry tests
# ---------------------------------------------------------------------------

class TestOptimizerRegistry:
    def test_list_optimizers_returns_sorted_list(self):
        result = list_optimizers()
        assert isinstance(result, list)
        assert result == sorted(result)
        assert "adam" in result
        assert "sgd" in result

    def test_build_optimizer_returns_stub(self):
        opt = build_optimizer("adam", lr=1e-3)
        assert opt is not None
        assert hasattr(opt, "apply_gradients")

    def test_build_optimizer_case_insensitive(self):
        opt = build_optimizer("Adam", lr=1e-4)
        assert opt is not None

    def test_build_optimizer_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unknown optimizer"):
            build_optimizer("nonexistent_optimizer")

    @pytest.mark.parametrize("name", ["adam", "sgd", "rmsprop", "adamw"])
    def test_build_optimizer_various_names(self, name):
        opt = build_optimizer(name, lr=1e-3)
        assert opt is not None


# ---------------------------------------------------------------------------
# CSV save/load roundtrip
# ---------------------------------------------------------------------------

class TestSaveLoadResults:
    def test_roundtrip(self, sample_results_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "results.csv")
            save_search_results(sample_results_df, path)
            loaded = load_search_results(path)
            assert len(loaded) == len(sample_results_df)
            assert list(loaded.columns) == list(sample_results_df.columns)

    def test_creates_parent_dirs(self, sample_results_df):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "results.csv")
            save_search_results(sample_results_df, path)
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# prune_dominated_configs tests
# ---------------------------------------------------------------------------

class TestPruneDominated:
    def test_removes_inferior_configs(self):
        # Dominance requires ALL metrics >= AND primary >.
        # Config 1 (iou=0.8, loss=0.6) dominates config 0 (iou=0.5, loss=0.5):
        #   0.8>=0.5 AND 0.6>=0.5 AND 0.8>0.5 → config 0 dominated
        # Config 2 (iou=0.3, loss=0.7) is not dominated (loss>0.6 fails)
        df = pd.DataFrame({
            "cfg_x": [1, 2, 3],
            "val_iou": [0.5, 0.8, 0.3],
            "val_loss": [0.5, 0.6, 0.7],
        })
        pruned = prune_dominated_configs(df, metric="val_iou")
        assert len(pruned) < len(df)

    def test_keeps_all_pareto_optimal(self):
        # Neither dominates: config 0 wins on iou (0.9>0.6) but config 1 wins
        # on loss (0.8>0.5) → no all->= relationship.
        df = pd.DataFrame({
            "cfg_x": [1, 2],
            "val_iou": [0.9, 0.6],
            "val_loss": [0.5, 0.8],
        })
        pruned = prune_dominated_configs(df, metric="val_iou")
        assert len(pruned) == 2  # Neither dominates the other

    def test_raises_on_missing_metric(self):
        df = pd.DataFrame({"cfg_x": [1], "val_iou": [0.5]})
        with pytest.raises(KeyError, match="not in results"):
            prune_dominated_configs(df, metric="nonexistent")

    def test_single_row_unchanged(self):
        df = pd.DataFrame({"cfg_x": [1], "val_iou": [0.5]})
        pruned = prune_dominated_configs(df, metric="val_iou")
        assert len(pruned) == 1
