"""Tests for multi-year patch loading in src.train."""

from __future__ import annotations

import json

import numpy as np

from src.train import ShardedArray, TrainConfig, load_data


def write_split(root, year: int, offset: float) -> None:
    year_dir = root / str(year)
    year_dir.mkdir(parents=True)
    split_counts = {"train": 2, "val": 1, "test": 1}
    for split, count in split_counts.items():
        x = np.full((count, 256, 256, 11), offset, dtype=np.float32)
        y = np.full((count, 256, 256), year % 2, dtype=np.uint8)
        np.save(year_dir / f"X_{split}.npy", x)
        np.save(year_dir / f"y_{split}.npy", y)


def test_load_data_concatenates_multiyear_manifest(tmp_path):
    write_split(tmp_path, 2020, 1.0)
    write_split(tmp_path, 2021, 2.0)
    manifest = {
        "years": [
            {"year": 2020, "output_dir": "2020"},
            {"year": 2021, "output_dir": "2021"},
        ]
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    x_train, y_train, x_val, y_val, x_test, y_test = load_data(TrainConfig(patches_path=tmp_path))

    assert x_train.shape == (4, 256, 256, 11)
    assert y_train.shape == (4, 256, 256)
    assert x_val.shape == (2, 256, 256, 11)
    assert y_val.shape == (2, 256, 256)
    assert x_test.shape == (2, 256, 256, 11)
    assert y_test.shape == (2, 256, 256)
    assert np.isclose(x_train[:2].mean(), 1.0)
    assert np.isclose(x_train[2:].mean(), 2.0)


def test_load_data_assigns_whole_years_to_temporal_splits(tmp_path):
    write_split(tmp_path, 2020, 1.0)
    write_split(tmp_path, 2021, 2.0)
    write_split(tmp_path, 2022, 3.0)
    manifest = {
        "split_strategy": "year_holdout",
        "train_years": [2020],
        "val_years": [2021],
        "test_years": [2022],
        "years": [
            {"year": 2020, "output_dir": "2020"},
            {"year": 2021, "output_dir": "2021"},
            {"year": 2022, "output_dir": "2022"},
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    x_train, y_train, x_val, y_val, x_test, y_test = load_data(TrainConfig(patches_path=tmp_path))

    assert x_train.shape == (4, 256, 256, 11)
    assert x_val.shape == (4, 256, 256, 11)
    assert x_test.shape == (4, 256, 256, 11)
    assert y_train.shape == y_val.shape == y_test.shape == (4, 256, 256)
    assert np.isclose(x_train.mean(), 1.0)
    assert np.isclose(x_val.mean(), 2.0)
    assert np.isclose(x_test.mean(), 3.0)
    assert isinstance(x_train, ShardedArray)
    np.testing.assert_allclose(x_train[[0, 3]], 1.0)
