#!/usr/bin/env python3
"""Build compact, validated lake and GLOF subsets for the Ile Alatau study AOI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box


ROOT = Path(__file__).resolve().parents[1]
AOI_BBOX = (75.5, 42.2, 78.2, 43.8)
AOI = gpd.GeoDataFrame(geometry=[box(*AOI_BBOX)], crs="EPSG:4326")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def build_tien_shan_lakes() -> dict:
    dataset_dir = ROOT / "data/lakes/tien_shan_1990_2023"
    source_dir = next(path for path in (dataset_dir / "source").iterdir() if path.is_dir())
    output = dataset_dir / "tien_shan_lakes_ile_alatau_1990_2023.gpkg"
    output.unlink(missing_ok=True)

    counts: dict[str, dict[str, int]] = {}
    for source in sorted(source_dir.glob("*.shp")):
        year = next(year for year in ("1990", "2000", "2010", "2020", "2023") if year in source.name)
        frame = gpd.read_file(source).to_crs("EPSG:4326")
        source_invalid = int((~frame.geometry.is_valid).sum())
        frame["geometry"] = frame.geometry.make_valid()
        frame = gpd.clip(frame, AOI, keep_geom_type=True)
        frame = frame[~frame.geometry.is_empty & frame.geometry.notna()].copy()
        frame.insert(0, "inventory_year", int(year))
        frame.to_file(output, layer=f"lakes_{year}", driver="GPKG")
        counts[year] = {
            "source_features": len(gpd.read_file(source)),
            "source_invalid_geometries": source_invalid,
            "aoi_features": len(frame),
            "aoi_invalid_geometries": int((~frame.geometry.is_valid).sum()),
        }

    source_zip = dataset_dir / "tien_shan_glacial_lakes_and_glof_1990_2023.zip"
    manifest = {
        "dataset": "Tien Shan glacial lakes, 1990-2023",
        "source": "Zenodo",
        "license": "CC-BY-4.0",
        "zenodo_record": 13208655,
        "doi": "10.5281/zenodo.13208655",
        "source_url": "https://zenodo.org/records/13208655",
        "aoi_bbox_epsg4326": list(AOI_BBOX),
        "processing": "Reprojected to EPSG:4326, make_valid, spatially clipped; originals retained.",
        "layers": counts,
        "artifacts": {
            str(source_zip.relative_to(ROOT)): {
                "bytes": source_zip.stat().st_size,
                "published_md5": "7e047083d3903f1625c3a4c62578fe15",
                "sha256": sha256(source_zip),
            },
            str(output.relative_to(ROOT)): {
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
            },
        },
        "claim_limit": "Inventory polygons are observations, not forecasts or validated hazard classes.",
    }
    write_manifest(dataset_dir / "manifest.json", manifest)
    return manifest


def build_glof_events() -> dict:
    dataset_dir = ROOT / "data/events/hmaglofdb"
    source_csv = next((dataset_dir / "source").rglob("HMAGLOFDB.csv"))
    frame = pd.read_csv(source_csv, encoding="cp1252", low_memory=False)
    valid_coords = frame["Lon_lake"].between(-180, 180) & frame["Lat_lake"].between(-90, 90)
    geo = gpd.GeoDataFrame(
        frame.loc[valid_coords].copy(),
        geometry=gpd.points_from_xy(
            frame.loc[valid_coords, "Lon_lake"],
            frame.loc[valid_coords, "Lat_lake"],
        ),
        crs="EPSG:4326",
    )
    subset = gpd.clip(geo, AOI)
    output = dataset_dir / "hmaglofdb_ile_alatau.gpkg"
    output.unlink(missing_ok=True)
    subset.to_file(output, layer="glof_events", driver="GPKG")

    source_zip = dataset_dir / "HMAGLOFDB-v1.3.0.zip"
    manifest = {
        "dataset": "High Mountain Asia Glacial Lake Outburst Flood Database",
        "version": "1.3.0",
        "source": "Zenodo",
        "license": "CC0-1.0",
        "zenodo_record": 18257243,
        "doi": "10.5281/zenodo.18257243",
        "source_url": "https://zenodo.org/records/18257243",
        "aoi_bbox_epsg4326": list(AOI_BBOX),
        "source_events": len(frame),
        "events_with_valid_lake_coordinates": len(geo),
        "aoi_events": len(subset),
        "artifacts": {
            str(source_zip.relative_to(ROOT)): {
                "bytes": source_zip.stat().st_size,
                "published_md5": "b6af9657ed28d793b058789835dd4ac8",
                "sha256": sha256(source_zip),
            },
            str(output.relative_to(ROOT)): {
                "bytes": output.stat().st_size,
                "sha256": sha256(output),
            },
        },
        "claim_limit": "Historical event evidence only; absence from the database is not evidence of no hazard.",
    }
    write_manifest(dataset_dir / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps({"lakes": build_tien_shan_lakes(), "events": build_glof_events()}, indent=2))
