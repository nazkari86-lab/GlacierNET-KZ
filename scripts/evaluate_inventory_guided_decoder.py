#!/usr/bin/env python3
"""Freeze an inventory-guided decoder in Ile Alatau and replay it externally.

This benchmark measures whether a declared historical-inventory search prior
prevents catastrophic overmapping.  It does not convert RGI-derived labels into
independent truth and therefore cannot unlock the strict external evidence gate.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_provisional_glacier_cohort import (  # noqa: E402
    _label_for_geometry,
    _read_s2_features,
    _window_for_geometry,
    metrics_for_table,
    select_stratified_glaciers,
)
from scripts.evaluate_provisional_zhetysu_external import _features  # noqa: E402
from src.benchmark_metrics import bootstrap_confidence_intervals, complete_segmentation_metrics  # noqa: E402
from src.inventory_guided_decoding import (  # noqa: E402
    InventoryGuidedDecoderConfig,
    inventory_guided_decode,
)
from src.provenance import sha256_file  # noqa: E402

OUTPUT_DIR = ROOT / "benchmarks/v2/provisional"
REPORT_PATH = OUTPUT_DIR / "inventory_guided_decoder_2024.json"
TABLE_PATH = OUTPUT_DIR / "inventory_guided_decoder_zhetysu_2024_per_glacier.csv"
EXTERNAL_SUMMARY = OUTPUT_DIR / "zhetysu_candidate_rgi_2024_summary.json"
EXTERNAL_BASELINE_TABLE = OUTPUT_DIR / "zhetysu_candidate_rgi_2024_per_glacier.csv"

THRESHOLD_GRID = (0.2, 0.3, 0.4, 0.5, 0.6)
BUFFER_GRID_M = (100.0, 200.0, 300.0)
METRICS = ("hard_dice", "hard_iou", "precision", "recall", "area_error_percent")


def _metric_record(label: np.ndarray, prediction: np.ndarray) -> dict[str, Any]:
    return metrics_for_table(
        complete_segmentation_metrics(
            label,
            prediction.astype(np.float32),
            threshold=0.5,
            pixel_area_m2=100.0,
            pixel_size=10.0,
        )
    )


def _mean(records: list[dict[str, Any]], field: str) -> float:
    return float(np.mean([float(record[field]) for record in records]))


def calibrate_in_ile_alatau() -> tuple[InventoryGuidedDecoderConfig, list[dict[str, Any]]]:
    """Select one decoder using only the declared Ile Alatau calibration cohort."""
    import geopandas as gpd
    import rasterio

    image_path = ROOT / "data/raw/sentinel2/sentinel2_2024.tif"
    rgi_path = ROOT / "data/rgi/rgi_study_area.shp"
    rgi = gpd.read_file(rgi_path)
    candidates: list[dict[str, Any]] = []
    with rasterio.open(image_path) as source:
        rgi = rgi.to_crs(source.crs)
        cohort = select_stratified_glaciers(rgi, per_class=6, seed=42)
        samples: list[tuple[np.ndarray, np.ndarray]] = []
        for _, glacier in cohort.iterrows():
            window = _window_for_geometry(source, glacier.geometry, buffer_m=500.0, max_pixels=1536)
            transform = source.window_transform(window)
            label = _label_for_geometry(
                glacier.geometry,
                shape=(int(window.height), int(window.width)),
                transform=transform,
            )
            ndsi = _read_s2_features(image_path, window)[..., 7]
            samples.append((ndsi, label))

        for buffer_m in BUFFER_GRID_M:
            for threshold in THRESHOLD_GRID:
                config = InventoryGuidedDecoderConfig(
                    ndsi_threshold=threshold,
                    support_buffer_m=buffer_m,
                    retain_inventory_connected_components=True,
                )
                rows = []
                for ndsi, label in samples:
                    prediction, _ = inventory_guided_decode(
                        ndsi,
                        label,
                        pixel_size_m=10.0,
                        config=config,
                    )
                    rows.append(_metric_record(label, prediction))
                candidates.append(
                    {
                        "config": config.to_dict(),
                        "n_glaciers": len(rows),
                        "mean_hard_dice": _mean(rows, "hard_dice"),
                        "mean_hard_iou": _mean(rows, "hard_iou"),
                        "mean_absolute_area_error_percent": _mean(
                            [{**row, "absolute": abs(float(row["area_error_percent"]))} for row in rows],
                            "absolute",
                        ),
                    }
                )

    candidates.sort(
        key=lambda row: (
            -float(row["mean_hard_dice"]),
            float(row["mean_absolute_area_error_percent"]),
            float(row["config"]["support_buffer_m"]),
        )
    )
    return InventoryGuidedDecoderConfig(**candidates[0]["config"]), candidates


def evaluate_external(config: InventoryGuidedDecoderConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply frozen parameters to the untouched provisional external geography."""
    import geopandas as gpd

    source_summary = json.loads(EXTERNAL_SUMMARY.read_text(encoding="utf-8"))
    rgi_path = ROOT / "data/rgi/RGI2000-v7.0-G-13_central_asia.shp"
    rgi = gpd.read_file(rgi_path)
    baseline_by_id: dict[str, dict[str, str]] = {}
    with EXTERNAL_BASELINE_TABLE.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            baseline_by_id[str(record["glacier_id"])] = record

    records: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    for source in source_summary["source_records"]:
        glacier_id = str(source["glacier_id"])
        features, transform, crs = _features(ROOT / source["path"])
        geometry = rgi.loc[rgi["rgi_id"] == glacier_id].to_crs(crs).geometry.iloc[0]
        label = _label_for_geometry(geometry, shape=features.shape[:2], transform=transform)
        prediction, diagnostics = inventory_guided_decode(
            features[..., 7],
            label,
            pixel_size_m=10.0,
            config=config,
        )
        metrics = _metric_record(label, prediction)
        baseline = baseline_by_id[glacier_id]
        record = {
            "glacier_id": glacier_id,
            "area_class": baseline["area_class"],
            **{field: metrics[field] for field in METRICS},
            "absolute_area_error_percent": abs(float(metrics["area_error_percent"])),
            "predicted_to_inventory_area_ratio": diagnostics["predicted_to_inventory_area_ratio"],
            "inventory_spectral_fraction": diagnostics["inventory_spectral_fraction"],
            "claim_tier": diagnostics["claim_tier"],
        }
        records.append(record)
        deltas.append(
            {
                "glacier_id": glacier_id,
                "hard_dice": float(record["hard_dice"]) - float(baseline["hard_dice"]),
                "hard_iou": float(record["hard_iou"]) - float(baseline["hard_iou"]),
                "absolute_area_error_percent": float(record["absolute_area_error_percent"])
                - abs(float(baseline["area_error_percent"])),
            }
        )

    summary = {
        "metrics_bootstrap": bootstrap_confidence_intervals(records, metrics=METRICS, seed=142),
        "mean_absolute_area_error_percent": _mean(records, "absolute_area_error_percent"),
        "paired_delta_decoder_minus_unconstrained_model": bootstrap_confidence_intervals(
            deltas,
            metrics=("hard_dice", "hard_iou", "absolute_area_error_percent"),
            seed=142,
        ),
    }
    return records, summary


def main() -> int:
    config, calibration_search = calibrate_in_ile_alatau()
    records, external = evaluate_external(config)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with TABLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)

    baseline = json.loads(EXTERNAL_SUMMARY.read_text(encoding="utf-8"))["metrics_bootstrap"]
    report = {
        "schema": "glaciernet-kz.inventory-guided-external-safeguard.v1",
        "status": "completed_provisional_inventory_guided_screening",
        "year": 2024,
        "method": (
            "NDSI physical evidence constrained to a buffered historical inventory search area; "
            "only components connected to the inventory are retained."
        ),
        "selection_protocol": {
            "calibration_geography": "Ile Alatau",
            "calibration_label_tier": "provisional_silver_rgi",
            "n_calibration_glaciers": 18,
            "objective": "maximum mean hard Dice, then minimum absolute area error",
            "threshold_grid": list(THRESHOLD_GRID),
            "support_buffer_grid_m": list(BUFFER_GRID_M),
            "selected_config": config.to_dict(),
            "candidate_results": calibration_search,
        },
        "external_replay": {
            "geography": "broad provisional Zhetysu candidate filter",
            "n_glaciers": len(records),
            "parameters_frozen_before_external_replay": True,
            "unconstrained_model_baseline": {
                "hard_dice": baseline["hard_dice"],
                "hard_iou": baseline["hard_iou"],
                "area_error_percent": baseline["area_error_percent"],
            },
            **external,
        },
        "claims_allowed": [
            "The frozen inventory-guided safeguard reduced catastrophic overmapping on this provisional replay.",
            "The result motivates inventory-guided candidate generation and abstaining review workflows.",
        ],
        "claims_not_allowed": [
            "independent external-region accuracy",
            "gold-label segmentation accuracy",
            "operational glacier-change accuracy",
            "proof that the current 2024 boundary equals the RGI-derived reference",
        ],
        "circularity_guard": (
            "RGI is used as both a search prior and provisional comparison layer. Metrics quantify inventory "
            "consistency and failure containment, not independent current-boundary accuracy."
        ),
        "artifacts": {
            "external_table": str(TABLE_PATH.relative_to(ROOT)),
            "external_table_sha256": sha256_file(TABLE_PATH),
            "baseline_summary": str(EXTERNAL_SUMMARY.relative_to(ROOT)),
            "baseline_summary_sha256": sha256_file(EXTERNAL_SUMMARY),
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
