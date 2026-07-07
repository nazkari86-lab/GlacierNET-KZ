"""Tests for src/ensemble.py — ensemble methods for glacier segmentation."""

from __future__ import annotations

import numpy as np
import pytest

from src.ensemble import (
    EnsembleConfig,
    EnsembleResult,
    majority_voting_ensemble,
    stacking_ensemble,
    weighted_average_ensemble,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pred_maps():
    """Three 32x32 probability maps with different glacier extent."""
    rng = np.random.default_rng(42)
    p1 = rng.random((32, 32)).astype(np.float32)
    p2 = rng.random((32, 32)).astype(np.float32)
    p3 = rng.random((32, 32)).astype(np.float32)
    return [p1, p2, p3]


@pytest.fixture
def perfect_agreement():
    """Three identical maps — models fully agree."""
    m = np.ones((16, 16), dtype=np.float32) * 0.8
    return [m.copy(), m.copy(), m.copy()]


@pytest.fixture
def ground_truth():
    """16x16 binary mask for stacking tests."""
    rng = np.random.default_rng(99)
    return rng.integers(0, 2, (16, 16)).astype(np.float32)


# ---------------------------------------------------------------------------
# Weighted Average Ensemble
# ---------------------------------------------------------------------------


class TestWeightedAverageEnsemble:
    def test_output_shapes(self, pred_maps):
        prob, mask, conf = weighted_average_ensemble(pred_maps)
        assert prob.shape == (32, 32)
        assert mask.shape == (32, 32)
        assert conf.shape == (32, 32)

    def test_prob_range(self, pred_maps):
        prob, _, _ = weighted_average_ensemble(pred_maps)
        assert prob.min() >= 0.0
        assert prob.max() <= 1.0

    def test_mask_is_binary(self, pred_maps):
        _, mask, _ = weighted_average_ensemble(pred_maps)
        assert set(np.unique(mask)).issubset({0, 1})

    def test_equal_weights_is_mean(self, pred_maps):
        prob, _, _ = weighted_average_ensemble(pred_maps)
        expected = np.mean(pred_maps, axis=0).astype(np.float32)
        np.testing.assert_allclose(prob, expected, atol=1e-5)

    def test_custom_weights(self, pred_maps):
        prob, _, _ = weighted_average_ensemble(pred_maps, weights=[1.0, 0.0, 0.0])
        np.testing.assert_allclose(prob, pred_maps[0], atol=1e-5)

    def test_weights_normalized(self, pred_maps):
        prob1, _, _ = weighted_average_ensemble(pred_maps, weights=[2.0, 2.0, 2.0])
        prob2, _, _ = weighted_average_ensemble(pred_maps, weights=[1.0, 1.0, 1.0])
        np.testing.assert_allclose(prob1, prob2, atol=1e-5)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            weighted_average_ensemble([])

    def test_zero_weights_raises(self, pred_maps):
        with pytest.raises(ValueError, match="positive"):
            weighted_average_ensemble(pred_maps, weights=[0.0, 0.0, 0.0])

    def test_confidence_perfect_agreement(self, perfect_agreement):
        _, _, conf = weighted_average_ensemble(perfect_agreement)
        assert conf.min() == pytest.approx(1.0, abs=1e-5)

    def test_threshold_effect(self, pred_maps):
        _, mask_low, _ = weighted_average_ensemble(pred_maps, threshold=0.3)
        _, mask_high, _ = weighted_average_ensemble(pred_maps, threshold=0.7)
        assert mask_low.sum() >= mask_high.sum()


# ---------------------------------------------------------------------------
# Majority Voting Ensemble
# ---------------------------------------------------------------------------


class TestMajorityVotingEnsemble:
    def test_output_shapes(self, pred_maps):
        prob, mask, conf = majority_voting_ensemble(pred_maps)
        assert prob.shape == (32, 32)
        assert mask.shape == (32, 32)

    def test_mask_binary(self, pred_maps):
        _, mask, _ = majority_voting_ensemble(pred_maps)
        assert set(np.unique(mask)).issubset({0, 1})

    def test_unanimous_agree(self):
        high = np.ones((8, 8), dtype=np.float32) * 0.9
        prob, mask, conf = majority_voting_ensemble([high, high, high])
        assert mask.sum() == 64

    def test_unanimous_disagree(self):
        low = np.ones((8, 8), dtype=np.float32) * 0.1
        _, mask, _ = majority_voting_ensemble([low, low, low])
        assert mask.sum() == 0

    def test_min_votes_override(self, pred_maps):
        _, mask_majority, _ = majority_voting_ensemble(pred_maps)
        _, mask_all, _ = majority_voting_ensemble(pred_maps, min_votes=3)
        assert mask_all.sum() <= mask_majority.sum()

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            majority_voting_ensemble([])

    def test_confidence_range(self, pred_maps):
        _, _, conf = majority_voting_ensemble(pred_maps)
        assert conf.min() >= 0.0
        assert conf.max() <= 1.0


# ---------------------------------------------------------------------------
# Stacking Ensemble
# ---------------------------------------------------------------------------


class TestStackingEnsemble:
    def test_without_ground_truth_is_mean(self, pred_maps):
        prob, mask, conf = stacking_ensemble(pred_maps, ground_truth=None)
        expected = np.mean(pred_maps, axis=0).astype(np.float32)
        np.testing.assert_allclose(prob, expected, atol=1e-5)

    def test_with_logistic_meta_learner(self):
        rng = np.random.default_rng(7)
        p1 = rng.random((16, 16)).astype(np.float32)
        p2 = rng.random((16, 16)).astype(np.float32)
        gt = (rng.random((16, 16)) > 0.5).astype(np.float32)
        prob, mask, conf = stacking_ensemble([p1, p2], ground_truth=gt, meta_learner="logistic")
        assert prob.shape == (16, 16)
        assert set(np.unique(mask)).issubset({0, 1})

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            stacking_ensemble([])


# ---------------------------------------------------------------------------
# EnsembleConfig
# ---------------------------------------------------------------------------


class TestEnsembleConfig:
    def test_default_valid(self):
        cfg = EnsembleConfig()
        assert cfg.validate() == []

    def test_invalid_method(self):
        cfg = EnsembleConfig(method="bad")
        assert len(cfg.validate()) > 0

    def test_invalid_threshold(self):
        cfg = EnsembleConfig(threshold=-0.1)
        assert len(cfg.validate()) > 0

    def test_invalid_n_models(self):
        cfg = EnsembleConfig(n_models=1)
        assert len(cfg.validate()) > 0


# ---------------------------------------------------------------------------
# EnsembleResult
# ---------------------------------------------------------------------------


class TestEnsembleResult:
    def test_construction(self, pred_maps):
        prob, mask, conf = weighted_average_ensemble(pred_maps)
        result = EnsembleResult(
            probability_map=prob,
            binary_mask=mask,
            confidence_map=conf,
            method="weighted",
            n_models=3,
            model_names=["unet", "attention_unet", "unet_pp"],
        )
        assert result.method == "weighted"
        assert result.n_models == 3
        assert result.individual_predictions is None
