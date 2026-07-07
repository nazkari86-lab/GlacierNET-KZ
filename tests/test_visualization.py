"""Tests for src/visualization.py — plot functions for glacier analysis."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.visualization import (
    plot_model_comparison,
    plot_prediction_grid,
    plot_training_curves,
    plot_trend_forecast,
    show_mask,
    show_rgb,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def close_figures():
    """Close all matplotlib figures after each test to prevent memory leaks."""
    yield
    plt.close("all")


@pytest.fixture
def sample_image_11ch():
    """128x128x11 float32 image."""
    return np.random.default_rng(0).random((128, 128, 11), dtype=np.float32)


@pytest.fixture
def sample_mask_2d():
    """128x128 uint8 binary mask."""
    return np.random.default_rng(1).integers(0, 2, (128, 128)).astype(np.uint8)


@pytest.fixture
def mock_history():
    """Minimal Keras-like history object."""
    h = MagicMock()
    h.history = {
        "loss": [0.5, 0.4, 0.3],
        "val_loss": [0.6, 0.45, 0.35],
        "dice_coefficient": [0.6, 0.7, 0.8],
        "val_dice_coefficient": [0.55, 0.65, 0.75],
    }
    return h


@pytest.fixture
def trend_data():
    """Sample glacier area trend data."""
    years = [2000, 2005, 2010, 2015, 2020]
    areas = [600.0, 550.0, 510.0, 480.0, 460.0]
    future_years = np.arange(2020, 2051)
    slope = -7.0
    intercept = 14600.0
    predicted = slope * future_years + intercept
    ci_lo = predicted - 20
    ci_hi = predicted + 20
    return years, areas, future_years, predicted, ci_lo, ci_hi


@pytest.fixture
def comparison_df():
    """DataFrame for model comparison chart."""
    return pd.DataFrame({
        "Метод": ["NDSI", "Random Forest", "U-Net", "Attention U-Net"],
        "F1-score": [0.65, 0.78, 0.87, 0.89],
    })


# ---------------------------------------------------------------------------
# show_rgb
# ---------------------------------------------------------------------------


class TestShowRgb:
    def test_returns_axes(self, sample_image_11ch):
        ax = show_rgb(sample_image_11ch)
        assert ax is not None

    def test_custom_title(self, sample_image_11ch):
        ax = show_rgb(sample_image_11ch, title="Test RGB")
        assert ax.get_title() == "Test RGB"

    def test_brightness_scaling(self, sample_image_11ch):
        ax1 = show_rgb(sample_image_11ch, brightness=1.0)
        ax2 = show_rgb(sample_image_11ch, brightness=5.0)
        assert ax1 is not None
        assert ax2 is not None

    def test_accepts_external_axes(self, sample_image_11ch):
        fig, ax = plt.subplots()
        returned = show_rgb(sample_image_11ch, ax=ax)
        assert returned is ax


# ---------------------------------------------------------------------------
# show_mask
# ---------------------------------------------------------------------------


class TestShowMask:
    def test_returns_axes(self, sample_mask_2d):
        ax = show_mask(sample_mask_2d)
        assert ax is not None

    def test_custom_cmap(self, sample_mask_2d):
        ax = show_mask(sample_mask_2d, cmap="Reds")
        assert ax is not None

    def test_title(self, sample_mask_2d):
        ax = show_mask(sample_mask_2d, title="Glacier Mask")
        assert ax.get_title() == "Glacier Mask"


# ---------------------------------------------------------------------------
# plot_training_curves
# ---------------------------------------------------------------------------


class TestPlotTrainingCurves:
    def test_returns_figure(self, mock_history):
        fig = plot_training_curves(mock_history)
        assert isinstance(fig, plt.Figure)

    def test_two_subplots(self, mock_history):
        fig = plot_training_curves(mock_history)
        assert len(fig.axes) == 2

    def test_save_path(self, mock_history, tmp_path):
        path = tmp_path / "curves.png"
        fig = plot_training_curves(mock_history, save_path=str(path))
        assert path.exists()


# ---------------------------------------------------------------------------
# plot_prediction_grid
# ---------------------------------------------------------------------------


class TestPlotPredictionGrid:
    def test_returns_figure(self, sample_image_11ch, sample_mask_2d):
        X = np.stack([sample_image_11ch] * 4)
        y = np.stack([sample_mask_2d] * 4)
        fig = plot_prediction_grid(X, y, y, n_examples=2)
        assert isinstance(fig, plt.Figure)

    def test_deterministic_with_rng(self, sample_image_11ch, sample_mask_2d):
        X = np.stack([sample_image_11ch] * 4)
        y = np.stack([sample_mask_2d] * 4)
        rng = np.random.default_rng(42)
        fig = plot_prediction_grid(X, y, y, n_examples=2, rng=rng)
        assert isinstance(fig, plt.Figure)


# ---------------------------------------------------------------------------
# plot_trend_forecast
# ---------------------------------------------------------------------------


class TestPlotTrendForecast:
    def test_returns_figure(self, trend_data):
        years, areas, fy, pred, ci_lo, ci_hi = trend_data
        fig = plot_trend_forecast(years, areas, fy, pred, ci_lo, ci_hi)
        assert isinstance(fig, plt.Figure)

    def test_custom_title(self, trend_data):
        years, areas, fy, pred, ci_lo, ci_hi = trend_data
        fig = plot_trend_forecast(years, areas, fy, pred, ci_lo, ci_hi, title="Custom")
        assert fig.axes[0].get_title() == "Custom"

    def test_save(self, trend_data, tmp_path):
        years, areas, fy, pred, ci_lo, ci_hi = trend_data
        path = tmp_path / "trend.png"
        plot_trend_forecast(years, areas, fy, pred, ci_lo, ci_hi, save_path=str(path))
        assert path.exists()


# ---------------------------------------------------------------------------
# plot_model_comparison
# ---------------------------------------------------------------------------


class TestPlotModelComparison:
    def test_returns_figure(self, comparison_df):
        fig = plot_model_comparison(comparison_df)
        assert isinstance(fig, plt.Figure)

    def test_save(self, comparison_df, tmp_path):
        path = tmp_path / "compare.png"
        plot_model_comparison(comparison_df, save_path=str(path))
        assert path.exists()
