#!/usr/bin/env python3
"""Download a compact automatic Zhetysu cohort and evaluate it as provisional external evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_provisional_glacier_cohort import (  # noqa: E402
    METRIC_FIELDS,
    _label_for_geometry,
    select_stratified_glaciers,
)
from src.benchmark_metrics import bootstrap_confidence_intervals, complete_segmentation_metrics  # noqa: E402
from src.data_loader import _append_sentinel2_indices  # noqa: E402
from src.model_security import verify_trusted_model  # noqa: E402
from src.models import get_custom_objects, predict_full_image  # noqa: E402

RAW_DIR = ROOT / "data/external/provisional_zhetysu_2024"
OUTPUT_DIR = ROOT / "benchmarks/v2/provisional"
# A transparent, broad geographic candidate filter; not an authoritative
# administrative or glaciological boundary definition.
ZHETYSU_CANDIDATE_BBOX = (79.0, 43.0, 84.1, 45.37)


def _is_candidate(frame):
    min_lon, min_lat, max_lon, max_lat = ZHETYSU_CANDIDATE_BBOX
    return frame.loc[
        frame["cenlon"].astype(float).between(min_lon, max_lon)
        & frame["cenlat"].astype(float).between(min_lat, max_lat)
    ].copy()


def _download_composite(geometry, *, destination: Path, year: int, buffer_degrees: float) -> None:
    import ee
    import requests

    minx, miny, maxx, maxy = geometry.bounds
    region = ee.Geometry.Rectangle(
        [minx - buffer_degrees, miny - buffer_degrees, maxx + buffer_degrees, maxy + buffer_degrees]
    )
    start, end = f"{year}-07-01", f"{year}-09-30"
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(["B2", "B3", "B4", "B8", "B8A", "B11", "B12"])
        .median()
    )
    terrain = ee.Terrain.products(ee.Image("USGS/SRTMGL1_003")).select(["elevation", "slope", "aspect"])
    image = s2.addBands(terrain).clip(region).toFloat()
    url = image.getDownloadURL(
        {
            "name": destination.stem,
            "scale": 10,
            "crs": "EPSG:32645",
            "region": region.getInfo()["coordinates"],
            "filePerBand": False,
            "format": "GEO_TIFF",
        }
    )
    response = requests.get(url, timeout=240)
    response.raise_for_status()
    if response.headers.get("content-type", "").split(";", 1)[0] != "image/tiff":
        raise ValueError(f"unexpected Earth Engine response for {destination.name}: {response.headers.get('content-type')}")
    destination.write_bytes(response.content)


def _features(path: Path) -> tuple[np.ndarray, object, object]:
    import rasterio

    with rasterio.open(path) as dataset:
        raw = np.moveaxis(dataset.read().astype(np.float32), 0, -1)
        transform, crs = dataset.transform, dataset.crs
    if raw.shape[-1] != 10:
        raise ValueError(f"{path.name}: expected 10 bands (7 S2 + 3 terrain), got {raw.shape[-1]}")
    s2 = raw[..., :7]
    s2 = np.clip(s2 / 10000.0, 0.0, 1.0)
    terrain = raw[..., 7:]
    terrain[..., 0] = np.clip(np.nan_to_num(terrain[..., 0]) / 7000.0, 0.0, 1.0)
    terrain[..., 1] = np.clip(np.nan_to_num(terrain[..., 1]) / 90.0, 0.0, 1.0)
    terrain[..., 2] = np.clip(np.nan_to_num(terrain[..., 2]) / 360.0, 0.0, 1.0)
    return np.concatenate([_append_sentinel2_indices(s2), terrain], axis=-1), transform, crs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--per-area-class", type=int, default=3)
    parser.add_argument("--seed", type=int, default=142)
    parser.add_argument("--buffer-degrees", type=float, default=0.01)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    import ee
    import geopandas as gpd
    import tensorflow as tf

    ee.Initialize()
    rgi = gpd.read_file(ROOT / "data/rgi/RGI2000-v7.0-G-13_central_asia.shp")
    cohort = select_stratified_glaciers(_is_candidate(rgi), per_class=args.per_area_class, seed=args.seed)
    model_path = ROOT / "models/unet_best_sentinel2_terrain_year_holdout_2016_2024"
    verify_trusted_model(model_path, root=ROOT)
    model = tf.keras.models.load_model(model_path, custom_objects=get_custom_objects(), compile=False)
    threshold = 0.2
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    source_records: list[dict[str, object]] = []
    for _, glacier in cohort.iterrows():
        glacier_id = str(glacier["rgi_id"])
        raw_path = RAW_DIR / f"{glacier_id}_{args.year}.tif"
        if args.refresh or not raw_path.exists():
            _download_composite(glacier.geometry, destination=raw_path, year=args.year, buffer_degrees=args.buffer_degrees)
        features, transform, crs = _features(raw_path)
        geometry = gpd.GeoSeries([glacier.geometry], crs=rgi.crs).to_crs(crs).iloc[0]
        label = _label_for_geometry(geometry, shape=features.shape[:2], transform=transform)
        probabilities, _ = predict_full_image(features, model, threshold=threshold)
        metrics = complete_segmentation_metrics(label, probabilities, threshold=threshold, pixel_area_m2=100.0, pixel_size=10.0)
        records.append(
            {
                "glacier_id": glacier_id,
                "area_km2_rgi": float(glacier["area_km2"]),
                "area_class": str(glacier["area_class"]),
                "model": "s2_terrain",
                "threshold": threshold,
                **metrics,
                "label_quality_tier": "provisional_silver_rgi",
                "evaluation_status": "external_geography_but_non_independent_rgi_pseudolabel",
            }
        )
        source_records.append(
            {
                "glacier_id": glacier_id,
                "path": str(raw_path.relative_to(ROOT)),
                "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                "source": "Google Earth Engine COPERNICUS/S2_SR_HARMONIZED + USGS/SRTMGL1_003",
            }
        )

    table = OUTPUT_DIR / f"zhetysu_candidate_rgi_{args.year}_per_glacier.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "schema": "glaciernet-kz.provisional-external-cohort.v1",
        "year": args.year,
        "geographic_candidate_bbox_wgs84": ZHETYSU_CANDIDATE_BBOX,
        "boundary_definition": "broad provisional geographic filter; not an authoritative Zhetysu boundary",
        "label_quality_tier": "provisional_silver_rgi",
        "evaluation_status": "external_geography_but_non_independent_rgi_pseudolabel",
        "claims_not_allowed": ["gold-label accuracy", "independent external validation", "operational accuracy"],
        "cohort_selection": {"per_area_class": args.per_area_class, "seed": args.seed, "n_glaciers": len(cohort)},
        "metrics_bootstrap": bootstrap_confidence_intervals(records, metrics=("hard_dice", "hard_iou", "recall", "area_error_percent"), seed=args.seed),
        "per_glacier_table": str(table.relative_to(ROOT)),
        "source_records": source_records,
    }
    (OUTPUT_DIR / f"zhetysu_candidate_rgi_{args.year}_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
