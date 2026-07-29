"""Unit tests for leakage-safe enhanced provisional training utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.build_enhanced_provisional_training_dataset import (
    assign_glacier_splits,
    normalize_window,
    patch_weights,
)
from src.models import build_data_generator


def test_split_assignment_keeps_glaciers_unique_and_stratified():
    rows = []
    for area_class, count in (("medium", 4), ("large", 5)):
        rows.extend({"glacier_id": f"{area_class}-{index}", "area_class": area_class} for index in range(count))
    labels = pd.DataFrame(rows)

    assignments = assign_glacier_splits(labels, seed=42)

    assert len(assignments) == 9
    assert set(assignments.values()) == {"train", "val", "test"}
    for area_class in ("medium", "large"):
        splits = {assignments[value] for value in labels[labels.area_class == area_class].glacier_id}
        assert splits == {"train", "val", "test"}
    assert assignments == assign_glacier_splits(labels, seed=42)


def test_normalization_and_review_weights_are_fail_safe():
    data = np.zeros((7, 4, 4), dtype=np.float32)
    data[:7] = 5000
    raw = np.ma.array(data, mask=False)
    image, valid = normalize_window(raw)
    assert image.shape == (4, 4, 11)
    assert np.allclose(image[..., :7], 0.5)
    assert valid.all()

    label = np.zeros((4, 4), dtype=np.uint8)
    label[1:3, 1:3] = 1
    review = np.zeros_like(label)
    review[1, 1] = 1
    valid[0, 0] = False
    weights = patch_weights(label, review, valid, quality_score=80)
    assert weights[2, 2] == np.float32(0.8)
    assert np.isclose(weights[1, 1], 0.16)
    assert weights[0, 0] == 0
    assert 0 <= weights.min() <= weights.max() <= 1


def test_data_generator_keeps_weight_map_aligned_during_augmentation():
    x = np.full((2, 16, 16, 11), 0.5, dtype=np.float32)
    y = np.zeros((2, 16, 16), dtype=np.uint8)
    y[:, 3:11, 5:13] = 1
    weights = np.where(y == 1, 0.8, 0.2).astype(np.float32)
    generator_class = build_data_generator()
    generator = generator_class(
        x,
        y,
        sample_weights=weights,
        batch_size=2,
        augment=True,
        shuffle=False,
        seed=17,
    )

    x_batch, y_batch, weight_batch = generator[0]

    assert x_batch.shape == x.shape
    assert y_batch.shape == (*y.shape, 1)
    assert weight_batch.shape == weights.shape
    np.testing.assert_allclose(weight_batch, np.where(y_batch[..., 0] == 1, 0.8, 0.2))
