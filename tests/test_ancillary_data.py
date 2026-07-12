"""Tests for ancillary-data helper functions that do not require remote services."""

from __future__ import annotations

import json

import numpy as np

from scripts.build_ancillary_features import terrain_derivatives
from scripts.build_ml_dataset_catalog import sentinel1_state
from scripts.build_multimodal_patches import normalize_sentinel1
from scripts.download_sentinel1_from_drive import expected_entries, update_entry_after_download
from scripts.evaluate_temporal_benchmark import report_payload
from scripts.export_sentinel1_ancillary import parse_years
from src.augmentation import AugmentationConfig, augment_patch


def test_terrain_derivatives_flat_surface_has_zero_slope():
    slope, aspect = terrain_derivatives(np.full((4, 4), 1200.0, dtype=np.float32), 10.0, -10.0)
    assert np.allclose(slope, 0.0)
    assert np.all((aspect >= 0.0) & (aspect < 360.0))


def test_parse_years_expands_ranges_and_removes_duplicates():
    assert parse_years("2016-2018,2017,2020") == [2016, 2017, 2018, 2020]


def test_sentinel1_state_reports_local_files_as_ready_without_manifest(tmp_path, monkeypatch):
    local = tmp_path / "sentinel1_2020.tif"
    local.write_bytes(b"test")
    monkeypatch.setattr("scripts.build_ml_dataset_catalog.ROOT", tmp_path)
    assert sentinel1_state([local]) == "ready"


def test_sentinel1_state_reports_partial_download(tmp_path, monkeypatch):
    sentinel_dir = tmp_path / "data/ancillary/sentinel1"
    sentinel_dir.mkdir(parents=True)
    (sentinel_dir / "export_manifest.json").write_text(
        '{"entries": [{"expected_filename": "sentinel1_2020.tif", "state": "submitted"}]}',
        encoding="utf-8",
    )
    local = sentinel_dir / "sentinel1_2020.tif"
    local.write_bytes(b"test")
    monkeypatch.setattr("scripts.build_ml_dataset_catalog.ROOT", tmp_path)
    assert sentinel1_state([local]) == "partial_download"


def test_sentinel1_download_manifest_only_accepts_submitted_entries(tmp_path):
    submitted = {"expected_filename": "sentinel1_2020.tif", "state": "submitted"}
    planned = {"expected_filename": "sentinel1_2021.tif", "state": "planned"}
    wanted = expected_entries({"entries": [submitted, planned]})
    assert wanted == {"sentinel1_2020.tif": submitted}

    target = tmp_path / "sentinel1_2020.tif"
    target.write_bytes(b"123")
    update_entry_after_download(submitted, target, 3)
    assert submitted["state"] == "downloaded"
    assert submitted["bytes"] == 3


def test_normalize_sentinel1_maps_db_and_clips_outliers():
    compact_db = np.array([[[-5000, -4000], [-2000, 0]]], dtype=np.int16)
    normalized = normalize_sentinel1(compact_db)
    np.testing.assert_allclose(normalized, [[[0.0, 0.0], [0.5, 1.0]]])


def test_temporal_benchmark_report_keeps_holdout_protocol(tmp_path, monkeypatch):
    manifest = {
        "train_years": [2020],
        "val_years": [2021],
        "test_years": [2022],
        "feature_schema": ["B2"],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr("scripts.evaluate_temporal_benchmark.ROOT", tmp_path.parent)
    payload = report_payload(tmp_path / "model", tmp_path, {"dice_coefficient": 0.8}, (2, 256, 256, 14))
    assert payload["test_years"] == [2022]
    assert payload["metrics"]["dice_coefficient"] == 0.8


def test_photometric_augmentation_preserves_signed_indices_and_terrain_channels():
    image = np.full((8, 8, 14), 0.5, dtype=np.float32)
    image[..., 7:11] = -0.5
    image[..., 11:] = 0.75
    mask = np.zeros((8, 8), dtype=np.uint8)
    cfg = AugmentationConfig(
        p_flip_lr=0.0,
        p_flip_ud=0.0,
        p_rotate90=0.0,
        p_brightness=0.0,
        p_contrast=0.0,
        p_gamma=1.0,
        p_gaussian_noise=0.0,
        p_gaussian_blur=0.0,
        p_channel_dropout=0.0,
        p_spectral_jitter=0.0,
    )

    augmented, _ = augment_patch(image, mask, np.random.default_rng(42), cfg, photometric_channels=7)

    assert np.isfinite(augmented).all()
    np.testing.assert_array_equal(augmented[..., 7:], image[..., 7:])
