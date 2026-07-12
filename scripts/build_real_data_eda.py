#!/usr/bin/env python3
"""Create a compact, reproducible EDA figure and band summary for one Sentinel-2 year."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


def rgb_display(rgb: np.ndarray) -> np.ndarray:
    """Clip a three-channel reflectance image to robust display percentiles."""
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected RGB array shaped (height, width, 3), got {rgb.shape}")
    lo, hi = np.nanpercentile(rgb, (2, 98))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return np.zeros_like(rgb, dtype=np.float32)
    return np.clip((rgb - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def output_shape(height: int, width: int, max_dimension: int) -> tuple[int, int]:
    scale = min(1.0, max_dimension / max(height, width))
    return max(1, round(height * scale)), max(1, round(width * scale))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2020)
    parser.add_argument("--max-dimension", type=int, default=1024)
    parser.add_argument("--figure", type=Path, default=None)
    parser.add_argument("--table", type=Path, default=None)
    args = parser.parse_args()
    if args.max_dimension < 32:
        raise ValueError("--max-dimension must be >= 32")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from rasterio.enums import Resampling

    source = config.DATA_RAW_SENTINEL2 / f"sentinel2_{args.year}.tif"
    mask = config.DATA_MASKS / f"mask_{args.year}.tif"
    if not source.exists() or not mask.exists():
        raise FileNotFoundError(f"Expected source and mask for {args.year}: {source}, {mask}")

    with rasterio.open(source) as dataset:
        if dataset.count < 7:
            raise ValueError(f"Expected at least 7 Sentinel-2 bands, found {dataset.count} in {source}")
        height, width = output_shape(dataset.height, dataset.width, args.max_dimension)
        # Sentinel source order: B2, B3, B4, B8, B8A, B11, B12.
        bands = dataset.read(
            indexes=tuple(range(1, 8)),
            out_shape=(7, height, width),
            resampling=Resampling.bilinear,
        ).astype(np.float32)
        source_dtype = dataset.dtypes[0]

    with rasterio.open(mask) as dataset:
        mask_small = dataset.read(1, out_shape=(height, width), resampling=Resampling.nearest).astype(bool)

    rgb = rgb_display(np.moveaxis(bands[[2, 1, 0]], 0, -1))
    rows = []
    for name, values in zip(config.S2_BANDS, bands):
        finite = values[np.isfinite(values)]
        rows.append(
            {
                "year": args.year,
                "band": name,
                "min": float(np.min(finite)),
                "p02": float(np.percentile(finite, 2)),
                "median": float(np.median(finite)),
                "mean": float(np.mean(finite)),
                "p98": float(np.percentile(finite, 98)),
                "max": float(np.max(finite)),
                "source_dtype": source_dtype,
                "display_height": height,
                "display_width": width,
            }
        )

    figure = args.figure or config.FIGURES_DIR / f"eda_sentinel2_{args.year}.png"
    table = args.table or config.TABLES_DIR / f"eda_sentinel2_{args.year}.csv"
    figure.parent.mkdir(parents=True, exist_ok=True)
    table.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(rgb)
    axes[0].set_title(f"Sentinel-2 RGB ({args.year})")
    axes[1].imshow(mask_small, cmap="Blues")
    axes[1].set_title("RGI training mask")
    axes[2].imshow(rgb)
    axes[2].imshow(np.ma.masked_where(~mask_small, mask_small), cmap="autumn", alpha=0.45)
    axes[2].set_title("RGB with glacier mask")
    for axis in axes:
        axis.set_axis_off()
    fig.tight_layout()
    fig.savefig(figure, dpi=180)
    plt.close(fig)

    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {figure}")
    print(f"Wrote {table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
