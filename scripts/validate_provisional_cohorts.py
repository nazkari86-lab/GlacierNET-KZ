#!/usr/bin/env python3
"""Validate local provisional cohorts without allowing them to upgrade scientific claims."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/v2/provisional"
NUMERIC_FIELDS = (
    "hard_dice",
    "hard_iou",
    "precision",
    "recall",
    "boundary_f1",
    "area_error_km2",
    "area_error_percent",
)


def _read_table(name: str, errors: list[str]) -> list[dict[str, str]]:
    path = BASE / name
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        errors.append(f"empty per-glacier table: {name}")
        return []
    for index, row in enumerate(rows, start=2):
        for field in NUMERIC_FIELDS:
            try:
                value = float(row[field])
            except (KeyError, ValueError):
                errors.append(f"{name}:{index}: invalid {field}")
                continue
            if not math.isfinite(value):
                errors.append(f"{name}:{index}: non-finite {field}")
        status = row.get("boundary_distance_status")
        distances = (row.get("hausdorff95_m", ""), row.get("assd_m", ""))
        if status == "finite":
            try:
                if not all(math.isfinite(float(value)) for value in distances):
                    raise ValueError
            except ValueError:
                errors.append(f"{name}:{index}: finite boundary status requires finite HD95/ASSD")
        elif status == "unbounded":
            if not all(value == "inf" for value in distances):
                errors.append(f"{name}:{index}: unbounded boundary status requires inf HD95/ASSD")
        else:
            errors.append(f"{name}:{index}: invalid boundary_distance_status")
    return rows


def validate() -> list[str]:
    errors: list[str] = []
    ile = json.loads((BASE / "ile_alatau_rgi_2024_paired_summary.json").read_text(encoding="utf-8"))
    if ile.get("label_quality_tier") != "provisional_silver_rgi":
        errors.append("Ile cohort must remain provisional_silver_rgi")
    if ile.get("evaluation_status") != "post_hoc_non_independent_not_a_holdout":
        errors.append("Ile cohort must remain non-independent")
    if ile.get("paired_analysis", {}).get("n_paired_glaciers", 0) < 15:
        errors.append("Ile paired cohort requires at least 15 glaciers")
    ile_table_path = BASE / "ile_alatau_rgi_2024_per_glacier.csv"
    if ile.get("per_glacier_table_sha256") != hashlib.sha256(ile_table_path.read_bytes()).hexdigest():
        errors.append("Ile per-glacier table hash mismatch")
    ile_rows = _read_table(ile_table_path.name, errors)
    ile_pairs: dict[str, set[str]] = {}
    for row in ile_rows:
        ile_pairs.setdefault(row["glacier_id"], set()).add(row["model"])
    if len(ile_pairs) != 18 or any(models != {"control", "s1"} for models in ile_pairs.values()):
        errors.append("Ile table must contain exactly one control/S1 pair for 18 glacier IDs")

    external = json.loads((BASE / "zhetysu_candidate_rgi_2024_summary.json").read_text(encoding="utf-8"))
    if external.get("label_quality_tier") != "provisional_silver_rgi":
        errors.append("external cohort must remain provisional_silver_rgi")
    if external.get("evaluation_status") != "external_geography_but_non_independent_rgi_pseudolabel":
        errors.append("external cohort must not be presented as independent validation")
    if external.get("cohort_selection", {}).get("n_glaciers", 0) < 9:
        errors.append("external provisional cohort requires nine glaciers")
    for source in external.get("source_records", []):
        path = ROOT / str(source.get("path", ""))
        if not path.is_file():
            errors.append(f"missing external source: {path.relative_to(ROOT)}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source.get("sha256"):
            errors.append(f"external source hash mismatch: {path.relative_to(ROOT)}")
        metadata = source.get("raster_metadata", {})
        if (
            metadata.get("bands") != 10
            or metadata.get("crs") != "EPSG:32645"
            or metadata.get("pixel_size_m") != [10.0, 10.0]
            or metadata.get("bytes") != path.stat().st_size
        ):
            errors.append(f"external raster metadata mismatch: {path.relative_to(ROOT)}")
        scenes = source.get("scene_provenance", {})
        if scenes.get("scene_count") != len(scenes.get("scene_ids", [])) or scenes.get("scene_count", 0) < 1:
            errors.append(f"invalid scene provenance: {path.relative_to(ROOT)}")
    external_table_path = BASE / "zhetysu_candidate_rgi_2024_per_glacier.csv"
    if external.get("per_glacier_table_sha256") != hashlib.sha256(external_table_path.read_bytes()).hexdigest():
        errors.append("external per-glacier table hash mismatch")
    external_rows = _read_table(external_table_path.name, errors)
    if len(external_rows) != 9 or len({row["glacier_id"] for row in external_rows}) != 9:
        errors.append("external table must contain exactly nine unique glacier IDs")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("PROVISIONAL COHORT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Provisional cohorts valid; strict gold/external evidence gate remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
