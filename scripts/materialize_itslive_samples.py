#!/usr/bin/env python3
"""Materialise real ITS_LIVE velocity samples for large RGI7 glaciers.

Only point time series at RGI centroids are downloaded. This preserves the
publisher's values while avoiding multi-terabyte cube replication.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fsspec
import geopandas as gpd
import numpy as np
import pandas as pd
import zarr
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data/external/centralasia_glacierbench/itslive"
RGI_PATH = ROOT / "data/rgi/RGI2000-v7.0-G-13_central_asia.shp"


def _epsg(href: str) -> int:
    match = re.search(r"EPSG(\d+)", href)
    if not match:
        raise ValueError(f"EPSG is absent from ITS_LIVE asset URL: {href}")
    return int(match.group(1))


def _inside(lon: float, lat: float, bbox: list[float]) -> bool:
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def _velocity_at_point(href: str, lon: float, lat: float) -> dict[str, float | int | None]:
    cube = zarr.open_consolidated(fsspec.get_mapper(href), mode="r")
    x, y = Transformer.from_crs(4326, _epsg(href), always_xy=True).transform(lon, lat)
    xs = cube["x"][:]
    ys = cube["y"][:]
    ix = int(np.argmin(np.abs(xs - x)))
    iy = int(np.argmin(np.abs(ys - y)))
    values: list[np.ndarray] = []
    time_chunk = int(cube["v"].chunks[0])
    for start in range(0, cube["v"].shape[0], time_chunk):
        stop = min(start + time_chunk, cube["v"].shape[0])
        values.append(cube["v"][start:stop, iy : iy + 1, ix : ix + 1].reshape(-1))
    speed = np.concatenate(values).astype(np.float64)
    missing = float(cube["v"].attrs.get("missing_value", -32767))
    valid = speed[(speed != missing) & np.isfinite(speed) & (speed >= 0)]
    return {
        "grid_x_m": float(xs[ix]),
        "grid_y_m": float(ys[iy]),
        "observations_total": int(speed.size),
        "observations_valid": int(valid.size),
        "velocity_m_per_year_median": float(np.median(valid)) if valid.size else None,
        "velocity_m_per_year_p90": float(np.percentile(valid, 90)) if valid.size else None,
        "velocity_m_per_year_max": float(np.max(valid)) if valid.size else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-samples", type=int, default=8)
    args = parser.parse_args()
    catalog_path = DATA_ROOT / "stac_cubes.json"
    if not catalog_path.is_file():
        raise FileNotFoundError("Run scripts/sync_centralasia_glacierbench.py first")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    glaciers = gpd.read_file(RGI_PATH)[["rgi_id", "glac_name", "cenlon", "cenlat", "area_km2"]].sort_values(
        "area_km2", ascending=False
    )

    candidates: list[dict[str, object]] = []
    used_cubes: set[str] = set()
    for record in glaciers.itertuples(index=False):
        for feature in catalog["features"]:
            href = feature["assets"]["zarr"]["href"]
            if href in used_cubes or not _inside(float(record.cenlon), float(record.cenlat), feature["bbox"]):
                continue
            candidates.append(
                {
                    "rgi_id": record.rgi_id,
                    "glacier_name": record.glac_name,
                    "longitude": float(record.cenlon),
                    "latitude": float(record.cenlat),
                    "rgi_area_km2": float(record.area_km2),
                    "cube_id": feature["id"],
                    "cube_url": href,
                }
            )
            used_cubes.add(href)
            break
        if len(candidates) >= args.max_samples:
            break

    rows: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {candidate['rgi_id']} from {candidate['cube_id']}", flush=True)
        sample = _velocity_at_point(
            str(candidate["cube_url"]),
            float(candidate["longitude"]),
            float(candidate["latitude"]),
        )
        rows.append({**candidate, **sample, "source": "NASA ITS_LIVE v2 cloud data cube"})
    if not rows:
        raise RuntimeError("No RGI7 glacier centroids intersect the ITS_LIVE catalogue")
    output = DATA_ROOT / "velocity_samples.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(output, index=False)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
