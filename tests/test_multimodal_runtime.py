from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.model_registry import S2_TERRAIN_S1_SCHEMA
from src.data_loader import load_image
from src.models import tta_predict_full_image
from src.multimodal_features import build_runtime_feature_stack, normalize_sentinel1, normalize_terrain


def _write_raster(path: Path, values: np.ndarray, transform) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=values.shape[-1],
        dtype=str(values.dtype),
        crs="EPSG:32642",
        transform=transform,
    ) as destination:
        destination.write(np.moveaxis(values, -1, 0))


def test_multimodal_normalizers_match_training_contract():
    terrain = normalize_terrain(np.array([[[3500.0, 45.0, 180.0]]], dtype=np.float32))
    sar = normalize_sentinel1(np.array([[[-2000, -4000]]], dtype=np.int16))
    np.testing.assert_allclose(terrain, 0.5)
    np.testing.assert_allclose(sar, np.array([[[0.5, 0.0]]], dtype=np.float32))


def test_pre_normalized_multimodal_stack_is_not_divided_twice(tmp_path: Path):
    transform = from_origin(0, 2, 1, 1)
    stack = np.full((2, 2, 16), 0.5, dtype=np.float32)
    path = tmp_path / "normalized_stack.tif"
    _write_raster(path, stack, transform)
    loaded = load_image(path)
    np.testing.assert_allclose(loaded[..., :7], 0.5)


def test_runtime_assembles_aligned_terrain_and_sar(tmp_path: Path):
    transform = from_origin(500000, 4800000, 10, 10)
    terrain = np.zeros((4, 4, 3), dtype=np.float32)
    terrain[..., 0] = 3500
    terrain[..., 1] = 45
    terrain[..., 2] = 180
    sar = np.zeros((4, 4, 2), dtype=np.int16)
    sar[..., 0] = -2000
    sar[..., 1] = -3000
    _write_raster(tmp_path / "data/ancillary/terrain/terrain_features.tif", terrain, transform)
    _write_raster(tmp_path / "data/ancillary/sentinel1/sentinel1_2024.tif", sar, transform)

    s2 = np.zeros((4, 4, 11), dtype=np.float32)
    stack, schema, warnings = build_runtime_feature_stack(
        s2,
        target_channels=16,
        transform=transform,
        crs="EPSG:32642",
        year=2024,
        root=tmp_path,
    )
    assert stack.shape == (4, 4, 16)
    assert schema == S2_TERRAIN_S1_SCHEMA
    np.testing.assert_allclose(stack[..., 11:14], 0.5)
    assert len(warnings) == 2


def test_runtime_rejects_sar_year_outside_validated_range(tmp_path: Path):
    with pytest.raises(ValueError, match="validated only"):
        build_runtime_feature_stack(
            np.zeros((4, 4, 11), dtype=np.float32),
            target_channels=16,
            transform=from_origin(0, 4, 1, 1),
            crs="EPSG:32642",
            year=2016,
            root=tmp_path,
        )


def test_sliding_window_tta_supports_non_patch_sized_scene():
    class FixedPatchModel:
        def predict(self, batch, verbose=0):
            assert batch.shape[1:3] == (256, 256)
            return batch[..., :1]

    image = np.zeros((300, 270, 1), dtype=np.float32)
    image[20:280, 20:250, 0] = 0.8
    probability, mask = tta_predict_full_image(FixedPatchModel(), image, threshold=0.5)
    assert probability.shape == image.shape[:2]
    assert mask.shape == image.shape[:2]
    assert mask[100, 100] == 1
    assert mask[0, 0] == 0
