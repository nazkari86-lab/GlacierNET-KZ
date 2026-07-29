#!/usr/bin/env python3
"""Validate the enhanced provisional annotation pack and fail closed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "glaciernet-kz.enhanced-provisional-annotations.v1"
TIER = "enhanced_provisional_multievidence"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory",
        type=Path,
        default=ROOT / "benchmarks/v2/annotations/enhanced_provisional",
    )
    args = parser.parse_args()
    directory = args.directory.resolve()
    manifest_path = directory / "manifest.json"
    queue_path = directory / "enhanced_annotation_queue.csv"
    errors: list[str] = []

    if not manifest_path.is_file() or not queue_path.is_file():
        raise FileNotFoundError("enhanced annotation manifest or queue is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        errors.append("unexpected manifest schema")
    if manifest.get("label_tier") != TIER or manifest.get("annotation_status") != "provisional_not_gold":
        errors.append("pack must remain explicitly provisional")
    if "independent expert gold-label accuracy" not in set(manifest.get("prohibited_claims", [])):
        errors.append("gold-label claim must be prohibited")

    with queue_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cohort = manifest.get("cohort", {})
    expected = int(cohort.get("tasks", 0))
    if len(rows) != expected or expected < 1:
        errors.append(f"queue size mismatch: expected {expected}, got {len(rows)}")
    if any(row.get("label_tier") != TIER for row in rows):
        errors.append("queue contains an unexpected label tier")
    if any(row.get("annotation_status") != "provisional_not_gold" for row in rows):
        errors.append("queue contains a non-provisional annotation status")
    if any(row.get("human_review_status") != "pending" for row in rows):
        errors.append("machine-generated rows cannot be marked reviewed")

    for output in manifest.get("outputs", []):
        path = ROOT / output["path"]
        if not path.is_file():
            errors.append(f"missing output: {output['path']}")
        elif sha256(path) != output.get("sha256"):
            errors.append(f"checksum mismatch: {output['path']}")
    project_info = manifest.get("qgis_project", {})
    if project_info:
        project_path = ROOT / project_info.get("path", "")
        if not project_path.is_file():
            errors.append("QGIS annotation project is missing")
        elif sha256(project_path) != project_info.get("sha256"):
            errors.append("QGIS annotation project checksum mismatch")
        if int(project_info.get("layer_count", 0)) < 16:
            errors.append("QGIS annotation project has too few evidence layers")
        if project_info.get("source_rasters_duplicated") is not False:
            errors.append("QGIS project must reference source rasters without duplicating them")
    preview_info = manifest.get("qa_preview", {})
    if preview_info:
        preview_path = ROOT / preview_info.get("path", "")
        if not preview_path.is_file():
            errors.append("annotation QA preview is missing")
        elif sha256(preview_path) != preview_info.get("sha256"):
            errors.append("annotation QA preview checksum mismatch")
        if len(preview_info.get("cases", [])) < 6:
            errors.append("annotation QA preview must include high- and low-confidence cases")

    years = [int(year) for year in cohort.get("years", [])]
    glacier_count = int(cohort.get("glaciers", 0))
    reference_grid = None
    for year in years:
        gpkg = directory / f"enhanced_labels_{year}.gpkg"
        raster = directory / f"label_classes_{year}.tif"
        if not gpkg.is_file() or not raster.is_file():
            errors.append(f"missing year outputs for {year}")
            continue
        labels = gpd.read_file(gpkg, layer="glacier_labels")
        reviews = gpd.read_file(gpkg, layer="review_zones")
        if len(labels) != glacier_count or len(reviews) != glacier_count:
            errors.append(f"unexpected feature count for {year}")
        if labels.crs is None or labels.crs.to_epsg() != 32642:
            errors.append(f"label CRS for {year} must be EPSG:32642")
        if not labels.geometry.is_valid.all():
            errors.append(f"invalid label geometry for {year}")
        empty_rows = labels[labels.geometry.is_empty]
        if any(
            row.get("confidence") != "low_provisional"
            or "empty_candidate" not in str(row.get("flags", "")).split("|")
            or int(row.get("review_priority", 0)) < 90
            for _, row in empty_rows.iterrows()
        ):
            errors.append(f"uncontrolled empty label geometry for {year}")
        if reviews.geometry.is_empty.any() or not reviews.geometry.is_valid.all():
            errors.append(f"empty or invalid review geometry for {year}")
        if set(labels["label_tier"]) != {TIER}:
            errors.append(f"wrong label tier in {year} GeoPackage")
        with rasterio.open(raster) as dataset:
            grid = (dataset.crs, dataset.transform, dataset.shape)
            if reference_grid is None:
                reference_grid = grid
            elif grid != reference_grid:
                errors.append(f"raster grid mismatch for {year}")
            values = set(dataset.read(1).ravel().tolist())
            if not values.issubset({0, 1, 2}) or 1 not in values or 2 not in values:
                errors.append(f"invalid class values for {year}: {sorted(values)}")

    if (
        len(
            set(
                manifest.get("excluded_inputs", {}).get("annual_processed_masks", {}).get("sha256_by_year", {}).values()
            )
        )
        > 1
    ):
        errors.append("excluded annual masks are no longer identical; reassess whether they can contribute evidence")
    if errors:
        print("ENHANCED PROVISIONAL ANNOTATION PACK INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        f"Enhanced provisional annotation pack valid: {len(rows)} tasks, "
        f"{glacier_count} glaciers, years {years}; human review remains pending."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
