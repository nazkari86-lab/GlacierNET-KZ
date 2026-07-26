#!/usr/bin/env python3
"""Evaluate paired models per RGI glacier without misrepresenting pseudo-labels as gold."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_multimodal_patches import normalize_sentinel1  # noqa: E402
from src.benchmark_metrics import bootstrap_confidence_intervals, complete_segmentation_metrics  # noqa: E402
from src.data_loader import _append_sentinel2_indices  # noqa: E402
from src.model_security import verify_trusted_model  # noqa: E402
from src.models import get_custom_objects, predict_full_image  # noqa: E402
from src.provenance import sha256_directory, sha256_file  # noqa: E402

DEFAULT_OUTPUT = ROOT / "benchmarks/v2/provisional"
METRIC_FIELDS = (
    "glacier_id",
    "area_km2_rgi",
    "area_class",
    "model",
    "threshold",
    "hard_dice",
    "hard_iou",
    "precision",
    "recall",
    "boundary_f1",
    "hausdorff95_m",
    "assd_m",
    "boundary_distance_status",
    "true_area_km2",
    "predicted_area_km2",
    "area_error_km2",
    "absolute_area_error_km2",
    "area_error_percent",
    "tp",
    "fp",
    "fn",
    "tn",
    "label_quality_tier",
    "evaluation_status",
)


def project_relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def select_stratified_glaciers(frame, *, per_class: int, seed: int):
    """Select deterministic small/medium/large RGI cohorts by area terciles."""
    if per_class < 1:
        raise ValueError("per_class must be positive")
    import pandas as pd

    selected = frame.loc[frame["area_km2"].astype(float) > 0].copy()
    selected["area_class"] = pd.qcut(selected["area_km2"].astype(float), q=3, labels=("small", "medium", "large"))
    pieces = []
    for area_class in ("small", "medium", "large"):
        group = selected.loc[selected["area_class"] == area_class]
        if len(group) < per_class:
            raise ValueError(f"not enough {area_class} glaciers for cohort")
        pieces.append(group.sample(n=per_class, random_state=seed + len(pieces)).sort_values("rgi_id"))
    return pd.concat(pieces, ignore_index=True)


def _window_for_geometry(dataset, geometry, *, buffer_m: float, max_pixels: int):
    import rasterio.windows

    bounds = geometry.bounds
    window = rasterio.windows.from_bounds(*bounds, transform=dataset.transform)
    pad = int(np.ceil(buffer_m / max(dataset.res)))
    window = window.round_offsets().round_lengths()
    window = rasterio.windows.Window(window.col_off - pad, window.row_off - pad, window.width + 2 * pad, window.height + 2 * pad)
    full = rasterio.windows.Window(0, 0, dataset.width, dataset.height)
    window = window.intersection(full).round_offsets().round_lengths()
    if max(window.width, window.height) > max_pixels:
        raise ValueError("glacier crop exceeds max_pixels; reduce cohort or increase limit")
    return window


def _read_s2_features(path: Path, window) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        array = np.moveaxis(dataset.read(window=window).astype(np.float32), 0, -1)
    array[..., :7] = np.clip(array[..., :7] / 10000.0, 0.0, 1.0)
    if array.shape[-1] == 7:
        array = _append_sentinel2_indices(array)
    return np.nan_to_num(array, nan=0.0, posinf=1.0, neginf=0.0)


def _read_terrain(path: Path, window) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        terrain = np.moveaxis(dataset.read(window=window).astype(np.float32), 0, -1)
    terrain[..., 0] = np.clip(np.nan_to_num(terrain[..., 0]) / 7000.0, 0.0, 1.0)
    terrain[..., 1] = np.clip(np.nan_to_num(terrain[..., 1]) / 90.0, 0.0, 1.0)
    terrain[..., 2] = np.clip(np.nan_to_num(terrain[..., 2]) / 360.0, 0.0, 1.0)
    return terrain


def _read_s1(path: Path, window) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        sar = np.moveaxis(dataset.read(window=window), 0, -1)
    return normalize_sentinel1(sar)


def _label_for_geometry(geometry, *, shape: tuple[int, int], transform) -> np.ndarray:
    from rasterio.features import rasterize

    return rasterize([(geometry, 1)], out_shape=shape, transform=transform, fill=0, dtype="uint8")


def metrics_for_table(metrics: dict[str, object]) -> dict[str, object]:
    """Map library metric names to explicit physical-unit table columns."""
    output = dict(metrics)
    output["hausdorff95_m"] = output.pop("hausdorff95")
    output["assd_m"] = output.pop("assd")
    distances = (float(output["hausdorff95_m"]), float(output["assd_m"]))
    output["boundary_distance_status"] = "finite" if all(math.isfinite(value) for value in distances) else "unbounded"
    return output


def _paired_deltas(records: list[dict[str, object]]) -> list[dict[str, object]]:
    pairs: dict[str, dict[str, dict[str, object]]] = {}
    for record in records:
        pairs.setdefault(str(record["glacier_id"]), {})[str(record["model"])] = record
    required = {"control", "s1"}
    matched = [pair for pair in pairs.values() if required <= set(pair)]
    if not matched:
        raise ValueError("no paired control/S1 glacier records")
    deltas: list[dict[str, object]] = []
    for glacier_id, pair in ((key, value) for key, value in pairs.items() if required <= set(value)):
        control, candidate = pair["control"], pair["s1"]
        deltas.append(
            {
                "glacier_id": glacier_id,
                "area_class": str(control["area_class"]),
                "hard_dice": float(candidate["hard_dice"]) - float(control["hard_dice"]),
                "hard_iou": float(candidate["hard_iou"]) - float(control["hard_iou"]),
                "precision": float(candidate["precision"]) - float(control["precision"]),
                "recall": float(candidate["recall"]) - float(control["recall"]),
                "absolute_area_error_km2": abs(float(candidate["area_error_km2"])) - abs(float(control["area_error_km2"])),
            }
        )
    return deltas


def paired_analysis(records: list[dict[str, object]], *, seed: int) -> dict[str, object]:
    """Return paired CIs, Wilcoxon tests, win rates, and area-class diagnostics."""
    from scipy.stats import wilcoxon

    deltas = _paired_deltas(records)
    metrics = ("hard_dice", "hard_iou", "precision", "recall", "absolute_area_error_km2")
    tests: dict[str, dict[str, float | int | str]] = {}
    for metric in metrics:
        values = np.asarray([float(row[metric]) for row in deltas], dtype=np.float64)
        nonzero = values[values != 0]
        if len(nonzero):
            statistic, p_value = wilcoxon(nonzero, alternative="two-sided", method="auto")
        else:
            statistic, p_value = 0.0, 1.0
        improvement = values < 0 if metric == "absolute_area_error_km2" else values > 0
        tests[metric] = {
            "test": "paired_wilcoxon_two_sided",
            "statistic": float(statistic),
            "p_value": float(p_value),
            "n_nonzero_pairs": int(len(nonzero)),
            "candidate_win_rate": float(improvement.mean()),
        }
    subgroups: dict[str, object] = {}
    for area_class in ("small", "medium", "large"):
        rows = [row for row in deltas if row["area_class"] == area_class]
        if rows:
            subgroups[area_class] = bootstrap_confidence_intervals(rows, metrics=metrics, seed=seed)
    return {
        "pairing_key": "glacier_id",
        "n_paired_glaciers": len(deltas),
        "candidate_minus_control": bootstrap_confidence_intervals(
            deltas,
            metrics=metrics,
            seed=seed,
        ),
        "paired_tests": tests,
        "area_class_subgroups": subgroups,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--per-area-class", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--buffer-m", type=float, default=500.0)
    parser.add_argument("--max-crop-pixels", type=int, default=1536)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    import geopandas as gpd
    import rasterio
    import tensorflow as tf

    image_path = ROOT / f"data/raw/sentinel2/sentinel2_{args.year}.tif"
    terrain_path = ROOT / "data/ancillary/terrain/terrain_features.tif"
    s1_path = ROOT / f"data/ancillary/sentinel1/sentinel1_{args.year}.tif"
    rgi_path = ROOT / "data/rgi/rgi_study_area.shp"
    models = {
        "control": (ROOT / "models/unet_best_sentinel2_terrain_control_year_holdout_2017_2024", 0.3, False),
        "s1": (ROOT / "models/unet_best_sentinel2_terrain_s1_year_holdout_2017_2024", 0.5, True),
    }
    for path in (image_path, terrain_path, s1_path, rgi_path):
        if not path.exists():
            raise FileNotFoundError(path)
    for model_path, _, _ in models.values():
        verify_trusted_model(model_path, root=ROOT)

    rgi = gpd.read_file(rgi_path)
    with rasterio.open(image_path) as source:
        rgi = rgi.to_crs(source.crs)
        cohort = select_stratified_glaciers(rgi, per_class=args.per_area_class, seed=args.seed)
        loaded_models = {
            key: tf.keras.models.load_model(path, custom_objects=get_custom_objects(), compile=False)
            for key, (path, _, _) in models.items()
        }
        records: list[dict[str, object]] = []
        for _, glacier in cohort.iterrows():
            window = _window_for_geometry(source, glacier.geometry, buffer_m=args.buffer_m, max_pixels=args.max_crop_pixels)
            transform = source.window_transform(window)
            label = _label_for_geometry(glacier.geometry, shape=(int(window.height), int(window.width)), transform=transform)
            s2 = _read_s2_features(image_path, window)
            terrain = _read_terrain(terrain_path, window)
            s1 = _read_s1(s1_path, window)
            for name, (_, threshold, uses_s1) in models.items():
                features = np.concatenate([s2, terrain, s1] if uses_s1 else [s2, terrain], axis=-1)
                probabilities, _ = predict_full_image(features, loaded_models[name], threshold=threshold)
                metrics = metrics_for_table(
                    complete_segmentation_metrics(
                        label,
                        probabilities,
                        threshold=threshold,
                        pixel_area_m2=100.0,
                        pixel_size=10.0,
                    )
                )
                records.append(
                    {
                        "glacier_id": str(glacier["rgi_id"]),
                        "area_km2_rgi": float(glacier["area_km2"]),
                        "area_class": str(glacier["area_class"]),
                        "model": name,
                        "threshold": threshold,
                        **metrics,
                        "label_quality_tier": "provisional_silver_rgi",
                        "evaluation_status": "post_hoc_non_independent_not_a_holdout",
                    }
                )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / f"ile_alatau_rgi_{args.year}_per_glacier.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "schema": "glaciernet-kz.provisional-glacier-cohort.v1",
        "year": args.year,
        "label_quality_tier": "provisional_silver_rgi",
        "evaluation_status": "post_hoc_non_independent_not_a_holdout",
        "claims_not_allowed": ["gold-label accuracy", "independent generalisation", "operational accuracy"],
        "cohort_selection": {"per_area_class": args.per_area_class, "seed": args.seed, "n_glaciers": len(cohort)},
        "paired_analysis": paired_analysis(records, seed=args.seed),
        "per_glacier_table": project_relative_or_absolute(csv_path),
        "per_glacier_table_sha256": sha256_file(csv_path),
        "input_provenance": {
            "rgi_sha256": sha256_file(rgi_path),
            "sentinel2_sha256": sha256_file(image_path),
            "terrain_sha256": sha256_file(terrain_path),
            "sentinel1_sha256": sha256_file(s1_path),
            "model_directory_sha256": {
                name: sha256_directory(path) for name, (path, _, _) in models.items()
            },
        },
    }
    summary_path = args.output_dir / f"ile_alatau_rgi_{args.year}_paired_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
