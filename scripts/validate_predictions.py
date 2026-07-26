#!/usr/bin/env python3
"""Validate local prediction coverage, georeferencing, masks, and area metadata."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import list_available_years  # noqa: E402
from src.provenance import PREDICTION_PROVENANCE_SCHEMA, sha256_file  # noqa: E402


def source_path(year: int) -> Path:
    sentinel2 = ROOT / "data" / "raw" / "sentinel2" / f"sentinel2_{year}.tif"
    landsat = ROOT / "data" / "raw" / "landsat" / f"landsat_{year}.tif"
    if sentinel2.is_file():
        return sentinel2
    if landsat.is_file():
        return landsat
    raise FileNotFoundError(f"No local source raster for {year}")


def validate_mask(mask_path: Path, source: Path, result: dict) -> list[str]:
    errors: list[str] = []
    if not mask_path.is_file():
        return [f"missing prediction mask: {mask_path.relative_to(ROOT)}"]
    if mask_path.is_symlink():
        errors.append(f"prediction mask is a symlink: {mask_path.relative_to(ROOT)}")
    with rasterio.open(source) as source_ds, rasterio.open(mask_path) as mask_ds:
        if mask_ds.crs != source_ds.crs:
            errors.append(f"CRS mismatch: {mask_path.relative_to(ROOT)}")
        if mask_ds.transform != source_ds.transform:
            errors.append(f"transform mismatch: {mask_path.relative_to(ROOT)}")
        if mask_ds.shape != source_ds.shape:
            errors.append(f"shape mismatch: {mask_path.relative_to(ROOT)}")
        if mask_ds.dtypes != ("uint8",):
            errors.append(f"mask must be uint8: {mask_path.relative_to(ROOT)}")
        mask = mask_ds.read(1)
        unique = set(int(value) for value in np.unique(mask))
        if not unique.issubset({0, 1}):
            errors.append(f"mask is not binary: {mask_path.relative_to(ROOT)} values={sorted(unique)}")
        expected_area = float(mask.sum(dtype=np.uint64)) * abs(mask_ds.res[0] * mask_ds.res[1]) / 1_000_000
        reported_area = result.get("area_km2")
        if reported_area is None or abs(float(reported_area) - expected_area) > 0.011:
            errors.append(
                f"area mismatch: {mask_path.relative_to(ROOT)} reported={reported_area}, calculated={expected_area:.4f}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    years = sorted({int(item["year"]) for item in list_available_years()})
    for year in years:
        prediction_dir = ROOT / "predictions" / str(year)
        results_path = prediction_dir / "results.json"
        if not results_path.is_file():
            errors.append(f"missing prediction results: {results_path.relative_to(ROOT)}")
            continue
        try:
            results = json.loads(results_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {results_path.relative_to(ROOT)}: {exc}")
            continue
        if "ndsi" not in results:
            errors.append(f"missing NDSI result for {year}")
        else:
            errors.extend(validate_mask(prediction_dir / "ndsi_mask.tif", source_path(year), results["ndsi"]))
        provenance_path = prediction_dir / "provenance.json"
        if not provenance_path.is_file():
            errors.append(f"missing prediction provenance: {provenance_path.relative_to(ROOT)}")
            continue
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {provenance_path.relative_to(ROOT)}: {exc}")
            continue
        if provenance.get("schema") != PREDICTION_PROVENANCE_SCHEMA:
            errors.append(f"invalid provenance schema for {year}")
        if provenance.get("year") != year:
            errors.append(f"provenance year mismatch for {year}")
        source = source_path(year)
        if provenance.get("source", {}).get("sha256") != sha256_file(source):
            errors.append(f"source SHA-256 mismatch in provenance for {year}")
        provenance_models = provenance.get("models", {})
        for model_name in results:
            if model_name not in provenance_models:
                errors.append(f"missing {model_name} provenance for {year}")
                continue
            mask_path = prediction_dir / f"{model_name}_mask.tif"
            if mask_path.is_file() and provenance_models[model_name].get("mask_sha256") != sha256_file(mask_path):
                errors.append(f"{model_name} mask SHA-256 mismatch in provenance for {year}")
            artifact_raw = provenance_models[model_name].get("model_artifact")
            if artifact_raw:
                artifact = ROOT / artifact_raw
                if not artifact.is_file():
                    errors.append(f"missing model artifact from provenance for {year}: {artifact_raw}")
                elif provenance_models[model_name].get("model_sha256") != sha256_file(artifact):
                    errors.append(f"{model_name} model SHA-256 mismatch in provenance for {year}")

    holdout_results_path = ROOT / "predictions" / "2024" / "results.json"
    holdout_results = json.loads(holdout_results_path.read_text(encoding="utf-8"))
    for model in ("rf", "unet"):
        if model not in holdout_results:
            errors.append(f"missing {model} holdout result for 2024")
        else:
            errors.extend(
                validate_mask(
                    ROOT / "predictions" / "2024" / f"{model}_mask.tif",
                    source_path(2024),
                    holdout_results[model],
                )
            )

    if errors:
        print("PREDICTION VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Prediction validation passed for {len(years)} years; RF and U-Net holdout masks verified for 2024.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
