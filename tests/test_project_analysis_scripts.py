"""Focused unit tests for deterministic local analysis helpers."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.analyze_rf_feature_importance import build_feature_rows
from scripts.build_real_data_eda import output_shape, rgb_display


def test_feature_rows_sort_descending_and_add_percentages():
    rows = build_feature_rows(["B2", "NDSI", "B11"], [0.2, 0.5, 0.3])
    assert [row["feature"] for row in rows] == ["NDSI", "B11", "B2"]
    assert rows[0]["rank"] == 1
    assert rows[0]["importance_percent"] == 50.0


def test_feature_rows_reject_mismatched_input_lengths():
    with pytest.raises(ValueError, match="does not match"):
        build_feature_rows(["B2"], [0.1, 0.2])


def test_rgb_display_and_output_shape_are_bounded():
    rgb = np.array([[[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]], dtype=np.float32)
    normalized = rgb_display(rgb)
    assert normalized.dtype == np.float32
    assert normalized.min() >= 0.0
    assert normalized.max() <= 1.0
    assert output_shape(5228, 8583, 1024) == (624, 1024)
