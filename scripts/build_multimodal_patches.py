#!/usr/bin/env python3
"""Build Sentinel-2 plus terrain patch datasets for multimodal glacier segmentation."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_multiyear_patches import parse_years, sample_patches, write_split  # noqa: E402
from src import config, data_loader, preprocessing  # noqa: E402

TERRAIN_FEATURES = ["elevation_m_normalized", "slope_degrees_normalized", "aspect_degrees_normalized"]
SENTINEL1_FEATURES = ["VV_dB_normalized", "VH_dB_normalized"]


def load_terrain(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        if dataset.count != 3:
            raise ValueError(f"Terrain file must have 3 bands: {path}")
        terrain = np.moveaxis(dataset.read().astype(np.float32), 0, -1)
    if terrain.shape[-1] != 3:
        raise ValueError(f"Unexpected terrain shape: {terrain.shape}")
    terrain[..., 0] = np.clip(np.nan_to_num(terrain[..., 0], nan=0.0) / 7000.0, 0.0, 1.0)
    terrain[..., 1] = np.clip(np.nan_to_num(terrain[..., 1], nan=0.0) / 90.0, 0.0, 1.0)
    terrain[..., 2] = np.clip(np.nan_to_num(terrain[..., 2], nan=0.0) / 360.0, 0.0, 1.0)
    return terrain


def normalize_sentinel1(db_x100: np.ndarray) -> np.ndarray:
    """Convert compact Sentinel-1 dB x100 exports to stable [0, 1] features."""
    db = db_x100.astype(np.float32) * 0.01
    return np.clip((db + 40.0) / 40.0, 0.0, 1.0)


def load_sentinel1(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        if dataset.count != 2:
            raise ValueError(f"Sentinel-1 file must have VV/VH bands: {path}")
        sar = np.moveaxis(dataset.read(), 0, -1)
    return normalize_sentinel1(sar)


def build_year(year: int, args: argparse.Namespace, terrain: np.ndarray) -> dict:
    image_path = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    mask_path = config.DATA_MASKS / f"mask_{year}.tif"
    if not image_path.exists() or not mask_path.exists():
        raise FileNotFoundError(f"Missing Sentinel-2 source or mask for {year}")
    image = data_loader.load_image(image_path)
    if image.shape[:2] != terrain.shape[:2]:
        raise ValueError(f"Terrain grid does not align with {image_path.name}: {terrain.shape} vs {image.shape}")
    feature_parts = [image, terrain]
    sentinel1_path = None
    if args.sentinel1_dir:
        sentinel1_path = args.sentinel1_dir / f"sentinel1_{year}.tif"
        if not sentinel1_path.exists():
            raise FileNotFoundError(f"Missing Sentinel-1 source for {year}: {sentinel1_path}")
        sar = load_sentinel1(sentinel1_path)
        if sar.shape[:2] != image.shape[:2]:
            raise ValueError(f"Sentinel-1 grid does not align with {image_path.name}: {sar.shape} vs {image.shape}")
        feature_parts.append(sar)
    features = np.concatenate(feature_parts, axis=-1)
    mask = data_loader.load_mask(mask_path)
    rng = np.random.default_rng(args.seed + year)
    x, y = preprocessing.create_patches(
        features,
        mask,
        patch_size=args.patch_size,
        stride=args.stride,
        min_glacier_fraction=args.min_glacier_fraction,
        background_keep_prob=args.background_keep_prob,
        rng=rng,
    )
    x, y = sample_patches(x, y, max_patches=args.max_patches_per_year, seed=args.seed + year)
    if len(x) == 0:
        raise ValueError(f"No patches created for {year}")
    out_dir = args.output_dir / str(year)
    split_stats = write_split(out_dir, x, y, seed=args.seed + year)
    return {
        "year": year,
        "source_file": str(image_path.relative_to(ROOT)),
        "mask_file": str(mask_path.relative_to(ROOT)),
        "terrain_file": str(args.terrain.resolve().relative_to(ROOT)),
        "sentinel1_file": str(sentinel1_path.relative_to(ROOT)) if sentinel1_path else None,
        "output_dir": str(out_dir.relative_to(ROOT)),
        "source_bands_loaded": int(features.shape[-1]),
        "patch_size": args.patch_size,
        "stride": args.stride,
        "patches_total": int(len(x)),
        "limited_by_max_patches": args.max_patches_per_year is not None,
        **split_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2016-2024")
    parser.add_argument("--output-dir", type=Path, default=config.DATA_PATCHES / "sentinel2_terrain_multiyear")
    parser.add_argument("--terrain", type=Path, default=ROOT / "data/ancillary/terrain/terrain_features.tif")
    parser.add_argument(
        "--sentinel1-dir",
        type=Path,
        default=None,
        help="Optional directory of verified Sentinel-1 VV/VH summer composites.",
    )
    parser.add_argument("--patch-size", type=int, default=config.PATCH_SIZE)
    parser.add_argument("--stride", type=int, default=config.PATCH_STRIDE)
    parser.add_argument("--min-glacier-fraction", type=float, default=config.MIN_GLACIER_FRACTION)
    parser.add_argument("--background-keep-prob", type=float, default=config.BACKGROUND_KEEP_PROB)
    parser.add_argument("--max-patches-per-year", type=int, default=None)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    args.terrain = args.terrain.resolve()
    if args.sentinel1_dir:
        args.sentinel1_dir = args.sentinel1_dir.resolve()
    years = parse_years(args.years)
    if 2015 in years:
        raise ValueError("2015 TOA fallback is excluded from strict multimodal Sentinel-2 training")
    if not args.terrain.exists():
        raise FileNotFoundError(f"Terrain features are missing: {args.terrain}")

    terrain = load_terrain(args.terrain)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_role": "multimodal_patch_generation",
        "split_strategy": "random_patch_split",
        "split_leakage_warning": "Use a year-held-out manifest before reporting generalization metrics.",
        "years_requested": years,
        "excluded_years": [2015],
        "channel_count": config.N_CHANNELS
        + len(TERRAIN_FEATURES)
        + (len(SENTINEL1_FEATURES) if args.sentinel1_dir else 0),
        "feature_schema": config.ALL_BAND_NAMES + TERRAIN_FEATURES + (SENTINEL1_FEATURES if args.sentinel1_dir else []),
        "years": [],
    }
    for year in years:
        print(f"Building multimodal patches for {year}...", flush=True)
        manifest["years"].append(build_year(year, args, terrain))

    path = args.output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote manifest -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
