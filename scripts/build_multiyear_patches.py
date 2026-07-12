#!/usr/bin/env python3
"""Build reproducible Sentinel-2 patch datasets for one or more years."""

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

from src import config, data_loader, preprocessing  # noqa: E402


def parse_years(raw: str) -> list[int]:
    years: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            years.extend(range(start, end + 1))
        else:
            years.append(int(part))
    return sorted(dict.fromkeys(years))


def load_rgi():
    import geopandas as gpd

    rgi_path = config.DATA_RGI / "rgi_study_area.shp"
    if not rgi_path.exists():
        raise FileNotFoundError(f"Missing RGI study-area shapefile: {rgi_path}")
    return gpd.read_file(rgi_path)


def sample_patches(
    x: np.ndarray,
    y: np.ndarray,
    *,
    max_patches: int | None,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    if max_patches is None or len(x) <= max_patches:
        return x, y
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), size=max_patches, replace=False)
    idx.sort()
    return x[idx], y[idx]


def write_split(out_dir: Path, x: np.ndarray, y: np.ndarray, seed: int) -> dict:
    x_train, x_val, x_test, y_train, y_val, y_test = preprocessing.train_val_test_split(x, y, seed=seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    arrays = {
        "X_train.npy": x_train.astype(np.float32),
        "X_val.npy": x_val.astype(np.float32),
        "X_test.npy": x_test.astype(np.float32),
        "y_train.npy": y_train.astype(np.uint8),
        "y_val.npy": y_val.astype(np.uint8),
        "y_test.npy": y_test.astype(np.uint8),
    }
    for name, arr in arrays.items():
        np.save(out_dir / name, arr)
    return {
        "split_strategy": "random_patch_split",
        "split_leakage_warning": (
            "Overlapping patches are split randomly. Use year-held-out or spatial split "
            "before reporting scientific generalization metrics."
        ),
        "train_patches": int(len(x_train)),
        "val_patches": int(len(x_val)),
        "test_patches": int(len(x_test)),
        "glacier_pixel_fraction": float(y.mean()),
    }


def build_year(year: int, args: argparse.Namespace, rgi) -> dict:
    image_path = config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif"
    if not image_path.exists():
        raise FileNotFoundError(f"Missing Sentinel-2 raster for {year}: {image_path}")

    mask_path = config.DATA_MASKS / f"mask_{year}.tif"
    if args.rebuild_masks or not mask_path.exists():
        preprocessing.rasterize_rgi_to_mask(rgi, image_path, mask_path)

    image = data_loader.load_image(image_path)
    if image.shape[-1] != config.N_CHANNELS:
        raise ValueError(f"{image_path.name}: expected {config.N_CHANNELS} channels, got {image.shape[-1]}")
    mask = data_loader.load_mask(mask_path)

    rng = np.random.default_rng(args.seed + year)
    x, y = preprocessing.create_patches(
        image,
        mask,
        patch_size=args.patch_size,
        stride=args.stride,
        min_glacier_fraction=args.min_glacier_fraction,
        background_keep_prob=args.background_keep_prob,
        rng=rng,
    )
    if len(x) == 0:
        raise ValueError(f"No patches created for {year}")
    x, y = sample_patches(x, y, max_patches=args.max_patches_per_year, seed=args.seed + year)

    out_dir = args.output_dir / str(year)
    split_stats = write_split(out_dir, x, y, seed=args.seed + year)
    return {
        "year": year,
        "source_file": str(image_path.relative_to(ROOT)),
        "mask_file": str(mask_path.relative_to(ROOT)),
        "output_dir": str(out_dir.resolve().relative_to(ROOT)),
        "source_bands_loaded": int(image.shape[-1]),
        "patch_size": args.patch_size,
        "stride": args.stride,
        "patches_total": int(len(x)),
        "limited_by_max_patches": args.max_patches_per_year is not None,
        **split_stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2016-2024", help="Comma/range list, for example 2016-2024 or 2021,2024")
    parser.add_argument("--output-dir", type=Path, default=config.DATA_PATCHES / "sentinel2_multiyear")
    parser.add_argument("--patch-size", type=int, default=config.PATCH_SIZE)
    parser.add_argument("--stride", type=int, default=config.PATCH_STRIDE)
    parser.add_argument("--min-glacier-fraction", type=float, default=config.MIN_GLACIER_FRACTION)
    parser.add_argument("--background-keep-prob", type=float, default=config.BACKGROUND_KEEP_PROB)
    parser.add_argument("--max-patches-per-year", type=int, default=None)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    parser.add_argument("--rebuild-masks", action="store_true")
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()

    years = parse_years(args.years)
    if 2015 in years:
        print("WARNING: 2015 is a late-year TOA fallback; exclude it from strict summer SR training if needed.")

    rgi = load_rgi()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "years_requested": years,
        "excluded_years": [2015] if 2015 not in years else [],
        "dataset_role": "patch_generation",
        "notes": [
            "Sentinel-2 rasters are loaded through src.data_loader.load_image().",
            "Compact 7-band rasters are expanded to 11 channels by deriving NDSI/NDWI/BSI/EVI locally.",
            "2015 is excluded by default because it is a late-year TOA fallback, not strict summer SR.",
            "Use held-out years or spatial splits for publication-grade validation.",
        ],
        "years": [],
    }

    for year in years:
        print(f"Building patches for {year}...")
        manifest["years"].append(build_year(year, args, rgi))

    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote manifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
