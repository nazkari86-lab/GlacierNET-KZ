#!/usr/bin/env python3
"""Align Copernicus DEM and ESA WorldCover to the Sentinel-2 training grid."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402


def terrain_derivatives(
    elevation: np.ndarray, x_resolution: float, y_resolution: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return slope degrees and clockwise aspect degrees for a projected DEM."""
    valid = np.isfinite(elevation)
    filled = np.where(valid, elevation, np.nanmedian(elevation[valid]))
    dz_dy, dz_dx = np.gradient(filled, abs(y_resolution), abs(x_resolution))
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy))).astype(np.float32)
    aspect = (np.degrees(np.arctan2(-dz_dx, dz_dy)) + 360.0) % 360.0
    slope[~valid] = np.nan
    aspect = aspect.astype(np.float32)
    aspect[~valid] = np.nan
    return slope, aspect


def source_bounds_in_wgs84(reference) -> tuple[float, float, float, float]:
    from rasterio.warp import transform_bounds

    return transform_bounds(reference.crs, "EPSG:4326", *reference.bounds, densify_pts=21)


def write_terrain(reference_path: Path, dem_paths: list[Path], output: Path) -> None:
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.merge import merge
    from rasterio.warp import Resampling, reproject

    with rasterio.open(reference_path) as reference, ExitStack() as stack:
        sources = [stack.enter_context(rasterio.open(path)) for path in dem_paths]
        mosaic, transform = merge(sources, bounds=source_bounds_in_wgs84(reference))
        source_profile = sources[0].profile.copy()
        source_profile.update(height=mosaic.shape[1], width=mosaic.shape[2], transform=transform, count=1)
        elevation = np.full((reference.height, reference.width), np.nan, dtype=np.float32)
        with MemoryFile() as memory:
            with memory.open(**source_profile) as dataset:
                dataset.write(mosaic[0], 1)
                reproject(
                    source=rasterio.band(dataset, 1),
                    destination=elevation,
                    src_transform=transform,
                    src_crs=dataset.crs,
                    dst_transform=reference.transform,
                    dst_crs=reference.crs,
                    src_nodata=dataset.nodata,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
        slope, aspect = terrain_derivatives(elevation, reference.transform.a, reference.transform.e)
        profile = reference.profile.copy()
        profile.update(count=3, dtype="float32", nodata=np.nan, compress="deflate", predictor=3, tiled=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output, "w", **profile) as dataset:
            dataset.write(elevation, 1)
            dataset.write(slope, 2)
            dataset.write(aspect, 3)
            dataset.set_band_description(1, "elevation_m")
            dataset.set_band_description(2, "slope_degrees")
            dataset.set_band_description(3, "aspect_degrees")


def write_worldcover(reference_path: Path, source_path: Path, output: Path) -> None:
    import rasterio
    from rasterio.warp import Resampling, reproject
    from rasterio.windows import from_bounds

    with rasterio.open(reference_path) as reference, rasterio.open(source_path) as source:
        bounds = source_bounds_in_wgs84(reference)
        window = from_bounds(*bounds, transform=source.transform).round_offsets().round_lengths()
        classes = source.read(1, window=window)
        class_transform = source.window_transform(window)
        aligned = np.zeros((reference.height, reference.width), dtype=np.uint8)
        reproject(
            source=classes,
            destination=aligned,
            src_transform=class_transform,
            src_crs=source.crs,
            src_nodata=source.nodata,
            dst_transform=reference.transform,
            dst_crs=reference.crs,
            dst_nodata=0,
            resampling=Resampling.nearest,
        )
        profile = reference.profile.copy()
        profile.update(count=1, dtype="uint8", nodata=0, compress="deflate", tiled=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output, "w", **profile) as dataset:
            dataset.write(aligned, 1)
            dataset.set_band_description(1, "esa_worldcover_2021_class")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=config.DATA_RAW_SENTINEL2 / "sentinel2_2020.tif")
    parser.add_argument("--dem-dir", type=Path, default=ROOT / "data/ancillary/copdem")
    parser.add_argument(
        "--worldcover",
        type=Path,
        default=ROOT / "data/ancillary/worldcover/ESA_WorldCover_10m_2021_v200_N42E075_Map.tif",
    )
    parser.add_argument("--terrain-output", type=Path, default=ROOT / "data/ancillary/terrain/terrain_features.tif")
    parser.add_argument(
        "--worldcover-output", type=Path, default=ROOT / "data/ancillary/worldcover/worldcover_2021_aligned.tif"
    )
    args = parser.parse_args()

    dem_paths = sorted(args.dem_dir.glob("Copernicus_DSM_COG_10_*_DEM.tif"))
    if len(dem_paths) < 1:
        raise FileNotFoundError(f"No Copernicus DEM tiles found in {args.dem_dir}")
    if not args.reference.exists() or not args.worldcover.exists():
        raise FileNotFoundError("Reference Sentinel-2 raster or WorldCover source is missing")

    write_terrain(args.reference, dem_paths, args.terrain_output)
    write_worldcover(args.reference, args.worldcover, args.worldcover_output)
    manifest = {
        "reference": str(args.reference.resolve().relative_to(ROOT)),
        "terrain": str(args.terrain_output.resolve().relative_to(ROOT)),
        "worldcover": str(args.worldcover_output.resolve().relative_to(ROOT)),
        "dem_sources": [str(path.resolve().relative_to(ROOT)) for path in dem_paths],
        "worldcover_source": str(args.worldcover.resolve().relative_to(ROOT)),
        "channels": ["elevation_m", "slope_degrees", "aspect_degrees", "esa_worldcover_2021_class"],
    }
    manifest_path = ROOT / "data/ancillary/manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {args.terrain_output}")
    print(f"Wrote {args.worldcover_output}")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
