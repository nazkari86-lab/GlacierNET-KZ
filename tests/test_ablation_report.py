"""Tests for controlled-ablation structural checks."""

from __future__ import annotations

import copy

import pytest

from scripts.build_ablation_report import validate_pair


def benchmark(channels: int = 14) -> dict:
    return {
        "train_years": [2017, 2018],
        "validation_years": [2019],
        "test_years": [2020],
        "test_patch_shape": [64, 256, 256, channels],
        "feature_schema": [f"c{index}" for index in range(channels)],
        "metrics": {
            "dice_coefficient": 0.8,
            "binary_io_u": 0.7,
            "precision": 0.9,
            "recall": 0.75,
        },
    }


def test_validate_pair_accepts_prefix_feature_ablation():
    control = benchmark()
    candidate = benchmark(16)
    validate_pair(control, candidate)


@pytest.mark.parametrize("mutation", ["split", "shape", "prefix", "metric"])
def test_validate_pair_rejects_non_comparable_reports(mutation):
    control = benchmark()
    candidate = benchmark(16)
    if mutation == "split":
        candidate["test_years"] = [2021]
    elif mutation == "shape":
        candidate["test_patch_shape"][0] = 32
    elif mutation == "prefix":
        candidate["feature_schema"][0] = "different"
    else:
        candidate["metrics"]["dice_coefficient"] = copy.copy(1.2)
    with pytest.raises(ValueError):
        validate_pair(control, candidate)
