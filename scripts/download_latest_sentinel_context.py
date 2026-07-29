#!/usr/bin/env python3
"""Export comparable summer Sentinel-2/Sentinel-1 composites for 2025–2026."""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
S2_REF = ROOT / "data/raw/sentinel2/sentinel2_2024.tif"
S1_REF = ROOT / "data/ancillary/sentinel1/sentinel1_2024.tif"


def export(image, path: Path, *, year: int, reference: Path, bands: int) -> None:
    import ee
    import rasterio

    with rasterio.open(reference) as ref:
        bounds, crs, shape = ref.bounds, ref.crs.to_string(), (ref.height, ref.width)
    import subprocess

    from rasterio.warp import transform_bounds

    paths = []
    for row in range(3):
        for col in range(4):
            x0 = bounds.left + (bounds.right - bounds.left) * col / 4
            x1 = bounds.left + (bounds.right - bounds.left) * (col + 1) / 4
            y0 = bounds.bottom + (bounds.top - bounds.bottom) * row / 3
            y1 = bounds.bottom + (bounds.top - bounds.bottom) * (row + 1) / 3
            west, south, east, north = transform_bounds(crs, "EPSG:4326", x0, y0, x1, y1, densify_pts=21)
            region = ee.Geometry.Rectangle([west, south, east, north])
            tile = path.with_name(f"{path.stem}_{row}_{col}.tif")
            paths.append(tile)
            url = image.clip(region).getDownloadURL(
                {
                    "name": tile.stem,
                    "region": region.getInfo()["coordinates"],
                    "crs": crs,
                    "scale": 10,
                    "format": "GEO_TIFF",
                    "filePerBand": False,
                }
            )
            r = requests.get(url, timeout=600)
            r.raise_for_status()
            tile.write_bytes(r.content)
    subprocess.run(["gdalbuildvrt", str(path.with_suffix(".vrt")), *map(str, paths)], check=True)
    subprocess.run(["gdal_translate", str(path.with_suffix(".vrt")), str(path)], check=True)
    return
    part = path.with_suffix(path.suffix + ".part")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with part.open("wb") as f:
            for c in r.iter_content(8 * 1024 * 1024):
                if c:
                    f.write(c)
    with rasterio.open(part) as d:
        if d.count != bands or d.crs.to_string() != crs or (d.height, d.width) != shape:
            raise RuntimeError(f"incompatible {year} export")
    part.replace(path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", nargs="+", type=int, default=[2025, 2026])
    a = p.parse_args()
    import ee

    ee.Initialize()
    for year in a.years:
        start, end = f"{year}-07-01", f"{year}-09-30"
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(start, end)
            .filterBounds(ee.Geometry.Rectangle([75.5, 42.4, 79.0, 44.1]))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
            .select(["B2", "B3", "B4", "B8", "B8A", "B11", "B12"])
            .median()
        )
        s1 = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterDate(start, end)
            .filterBounds(ee.Geometry.Rectangle([75.5, 42.4, 79.0, 44.1]))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .select(["VV", "VH"])
            .median()
        )
        export(s2, ROOT / f"data/raw/sentinel2/sentinel2_{year}.tif", year=year, reference=S2_REF, bands=7)
        export(s1, ROOT / f"data/ancillary/sentinel1/sentinel1_{year}.tif", year=year, reference=S1_REF, bands=2)
        print(f"completed {year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
