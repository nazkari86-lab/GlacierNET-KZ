"""Reproducible multimodal feature construction for training and inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import config
from .model_registry import S2_TERRAIN_S1_SCHEMA, S2_TERRAIN_SCHEMA


def normalize_terrain(values: np.ndarray) -> np.ndarray:
    terrain = np.asarray(values, dtype=np.float32).copy()
    if terrain.shape[-1] != 3:
        raise ValueError(f"terrain must have 3 channels, got {terrain.shape}")
    scales = np.asarray([7000.0, 90.0, 360.0], dtype=np.float32)
    terrain = np.nan_to_num(terrain, nan=0.0, posinf=0.0, neginf=0.0) / scales
    return np.clip(terrain, 0.0, 1.0).astype(np.float32)


def normalize_sentinel1(db_x100: np.ndarray) -> np.ndarray:
    """Convert compact Sentinel-1 dB x100 exports to stable [0, 1]."""
    sar = np.asarray(db_x100, dtype=np.float32)
    if sar.shape[-1] != 2:
        raise ValueError(f"Sentinel-1 must have VV/VH channels, got {sar.shape}")
    db = sar * 0.01
    return np.clip((db + 40.0) / 40.0, 0.0, 1.0).astype(np.float32)


def _reproject_channels(
    path: Path,
    *,
    count: int,
    dst_shape: tuple[int, int],
    dst_transform,
    dst_crs,
) -> np.ndarray:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    if dst_crs is None or dst_transform is None:
        raise ValueError("A georeferenced GeoTIFF is required for automatic ancillary feature alignment")
    if not path.is_file():
        raise FileNotFoundError(f"Required ancillary raster is missing: {path}")

    output = np.full((dst_shape[0], dst_shape[1], count), np.nan, dtype=np.float32)
    with rasterio.open(path) as source:
        if source.count != count:
            raise ValueError(f"{path.name} must contain {count} bands, found {source.count}")
        if source.crs is None:
            raise ValueError(f"Ancillary raster has no CRS: {path}")
        for index in range(count):
            reproject(
                source=rasterio.band(source, index + 1),
                destination=output[..., index],
                src_transform=source.transform,
                src_crs=source.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
                dst_nodata=np.nan,
            )
    if not np.isfinite(output).any():
        raise ValueError(f"Ancillary raster does not overlap the uploaded scene: {path.name}")
    return output


def build_runtime_feature_stack(
    sentinel2_features: np.ndarray,
    *,
    target_channels: int,
    transform,
    crs,
    year: int | None,
    root: Path = config.PROJECT_ROOT,
) -> tuple[np.ndarray, tuple[str, ...], list[str]]:
    """Append locally verified terrain/SAR rasters to 11-channel S2 features.

    Exact 14/16-channel pre-normalized stacks are accepted as-is.  An
    11-channel georeferenced scene is automatically aligned to local ancillary
    rasters, so the production API uses the same normalization as training.
    """
    features = np.asarray(sentinel2_features, dtype=np.float32)
    if features.ndim != 3:
        raise ValueError(f"Expected HxWxC features, got {features.shape}")
    if target_channels == 16:
        if year is None:
            raise ValueError("year is required to select the matching Sentinel-1 composite")
        if not 2017 <= int(year) <= 2024:
            raise ValueError("The deployed S2+terrain+SAR model is validated only for years 2017–2024")
    if features.shape[-1] == target_channels:
        schema = S2_TERRAIN_S1_SCHEMA if target_channels == 16 else S2_TERRAIN_SCHEMA
        return features, schema, ["Exact pre-normalized feature stack accepted in canonical band order."]
    if features.shape[-1] != config.N_CHANNELS:
        raise ValueError(
            f"Automatic multimodal assembly requires {config.N_CHANNELS} S2/index channels "
            f"or an exact {target_channels}-channel normalized stack; got {features.shape[-1]}."
        )
    if target_channels not in (14, 16):
        raise ValueError(f"Unsupported multimodal target channel count: {target_channels}")

    terrain_raw = _reproject_channels(
        root / "data/ancillary/terrain/terrain_features.tif",
        count=3,
        dst_shape=features.shape[:2],
        dst_transform=transform,
        dst_crs=crs,
    )
    parts = [features, normalize_terrain(terrain_raw)]
    warnings = ["Terrain was reprojected to the uploaded scene using the training normalization."]
    schema = S2_TERRAIN_SCHEMA
    if target_channels == 16:
        sar_raw = _reproject_channels(
            root / f"data/ancillary/sentinel1/sentinel1_{int(year)}.tif",
            count=2,
            dst_shape=features.shape[:2],
            dst_transform=transform,
            dst_crs=crs,
        )
        parts.append(normalize_sentinel1(sar_raw))
        warnings.append(f"Sentinel-1 {int(year)} VV/VH was aligned from the verified local composite.")
        schema = S2_TERRAIN_S1_SCHEMA

    stack = np.concatenate(parts, axis=-1).astype(np.float32)
    if stack.shape[-1] != target_channels or not np.isfinite(stack).all():
        raise ValueError(f"Invalid assembled feature stack: {stack.shape}")
    return stack, schema, warnings
