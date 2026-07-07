"""Tests for src/losses.py — loss function registry and individual losses."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("tensorflow", reason="TensorFlow required for loss function tests")


def _val(tensor_or_scalar) -> float:
    """Extract a plain float from a TF tensor or scalar."""
    if hasattr(tensor_or_scalar, "numpy"):
        return float(tensor_or_scalar.numpy())
    return float(tensor_or_scalar)


from src.losses import (
    LossConfig,
    bce_loss,
    boundary_dice_loss,
    build_loss,
    combined_bce_dice_loss,
    combined_focal_dice_loss,
    dice_coefficient,
    dice_loss,
    focal_loss,
    focal_tversky_loss,
    get_custom_objects,
    get_loss_fn,
    list_losses,
    tversky_loss,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def y_true():
    return np.array([[1, 1, 0, 0], [1, 0, 0, 0]], dtype=np.float32)


@pytest.fixture
def y_pred():
    return np.array([[0.9, 0.8, 0.1, 0.2], [0.7, 0.3, 0.1, 0.05]], dtype=np.float32)


@pytest.fixture
def y_perfect(y_true):
    return y_true.copy()


# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------


class TestDiceLoss:
    def test_perfect_prediction_gives_zero_loss(self, y_true, y_perfect):
        loss = _val(dice_loss(y_true, y_perfect))
        assert loss == pytest.approx(0.0, abs=1e-4)

    def test_dice_coefficient_perfect(self, y_true, y_perfect):
        coeff = _val(dice_coefficient(y_true, y_perfect))
        assert coeff == pytest.approx(1.0, abs=1e-4)

    def test_dice_loss_range(self, y_true, y_pred):
        loss = _val(dice_loss(y_true, y_pred))
        assert 0.0 <= loss <= 1.0

    def test_dice_coefficient_symmetric(self, y_true, y_pred):
        c1 = _val(dice_coefficient(y_true, y_pred))
        c2 = _val(dice_coefficient(y_pred, y_true))
        assert c1 == pytest.approx(c2, abs=1e-5)


# ---------------------------------------------------------------------------
# Focal
# ---------------------------------------------------------------------------


class TestFocalLoss:
    def test_focal_loss_positive(self, y_true, y_pred):
        loss = _val(focal_loss(y_true, y_pred))
        assert loss > 0

    def test_focal_loss_decreases_with_better_pred(self, y_true, y_perfect, y_pred):
        loss_bad = _val(focal_loss(y_true, y_pred))
        loss_good = _val(focal_loss(y_true, y_perfect))
        assert loss_good < loss_bad


# ---------------------------------------------------------------------------
# Tversky
# ---------------------------------------------------------------------------


class TestTverskyLoss:
    def test_perfect_prediction(self, y_true, y_perfect):
        loss = _val(tversky_loss(y_true, y_perfect))
        assert loss == pytest.approx(0.0, abs=1e-4)

    def test_range(self, y_true, y_pred):
        loss = _val(tversky_loss(y_true, y_pred))
        assert 0.0 <= loss <= 1.0

    def test_alpha_beta_asymmetry(self, y_true, y_pred):
        loss_fp = _val(tversky_loss(y_true, y_pred, alpha=0.7, beta=0.3))
        loss_fn = _val(tversky_loss(y_true, y_pred, alpha=0.3, beta=0.7))
        assert loss_fp != pytest.approx(loss_fn, abs=1e-4)


# ---------------------------------------------------------------------------
# Focal Tversky
# ---------------------------------------------------------------------------


class TestFocalTverskyLoss:
    def test_positive(self, y_true, y_pred):
        loss = _val(focal_tversky_loss(y_true, y_pred))
        assert loss >= 0

    def test_perfect(self, y_true, y_perfect):
        loss = _val(focal_tversky_loss(y_true, y_perfect))
        assert loss == pytest.approx(0.0, abs=1e-4)


# ---------------------------------------------------------------------------
# Combined losses
# ---------------------------------------------------------------------------


class TestCombinedLosses:
    def test_bce_dice_finite(self, y_true, y_pred):
        loss = _val(combined_bce_dice_loss(y_true, y_pred))
        assert np.isfinite(loss)

    def test_focal_dice_positive(self, y_true, y_pred):
        loss = _val(combined_focal_dice_loss(y_true, y_pred))
        assert loss > 0

    def test_bce_loss_finite(self, y_true, y_pred):
        loss = _val(bce_loss(y_true, y_pred))
        assert np.isfinite(loss)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestLossRegistry:
    def test_list_losses_not_empty(self):
        losses = list_losses()
        assert len(losses) >= 8
        assert "dice" in losses
        assert "focal" in losses
        assert "tversky" in losses

    def test_get_loss_fn_known(self):
        fn = get_loss_fn("dice")
        assert callable(fn)

    def test_get_loss_fn_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown loss"):
            get_loss_fn("nonexistent_loss")

    def test_get_loss_fn_with_kwargs(self, y_true, y_pred):
        fn = get_loss_fn("focal", alpha=0.5, gamma=1.0)
        loss = _val(fn(y_true, y_pred))
        assert loss > 0

    def test_get_custom_objects_keys(self):
        objs = get_custom_objects()
        assert "dice_loss" in objs
        assert "focal_loss" in objs
        assert "dice_coefficient" in objs


# ---------------------------------------------------------------------------
# LossConfig
# ---------------------------------------------------------------------------


class TestLossConfig:
    def test_default_config_valid(self):
        cfg = LossConfig()
        assert cfg.validate() == []

    def test_invalid_name(self):
        cfg = LossConfig(name="bad_name")
        errors = cfg.validate()
        assert len(errors) == 1

    def test_invalid_alpha(self):
        cfg = LossConfig(alpha=-0.1)
        errors = cfg.validate()
        assert any("alpha" in e for e in errors)

    def test_build_loss_from_config(self, y_true, y_pred):
        cfg = LossConfig(name="dice")
        fn = build_loss(cfg)
        loss = _val(fn(y_true, y_pred))
        assert loss >= 0
