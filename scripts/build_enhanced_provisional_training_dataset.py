#!/usr/bin/env python3
"""Build a leakage-safe training dataset from enhanced provisional labels.

Only ``high_provisional`` objects are eligible. All years of a glacier remain
in one split, review-zone pixels receive a lower training weight, and every
patch keeps geospatial provenance. The resulting dataset is useful for model
development, but it is not an independent gold-label benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.windows import Window, from_bounds
from shapely.geometry import box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402
from src.data_loader import _append_sentinel2_indices  # noqa: E402

ANNOTATION_DIR = ROOT / "benchmarks/v2/annotations/enhanced_provisional"
DEFAULT_OUTPUT = ROOT / "data/processed/patches/enhanced_provisional_spatial_holdout"
SCHEMA = "glaciernet-kz.enhanced-provisional-training.v1"
SPLIT_STRATEGY = "glacier_group_spatial_holdout"
ELIGIBLE_CONFIDENCE = "high_provisional"
SPLIT_ORDER = ("train", "val", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_rank(value: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def assign_glacier_splits(labels: pd.DataFrame, seed: int) -> dict[str, str]:
    """Stratify glaciers and balance estimated patch workload across splits."""
    frame = labels.copy()
    if "area_km2" not in frame:
        frame["area_km2"] = 1.0
    unique = frame.groupby(["glacier_id", "area_class"], as_index=False).agg(
        area_km2=("area_km2", "max"), task_count=("glacier_id", "size")
    )
    if unique["glacier_id"].duplicated().any():
        raise ValueError("A glacier has inconsistent area classes")

    options_by_class: list[list[dict[str, str]]] = []
    for area_class, group in unique.groupby("area_class", sort=True):
        ids = sorted(group["glacier_id"].astype(str), key=lambda value: stable_rank(value, seed))
        count = len(ids)
        if count < 3:
            raise ValueError(f"Need at least three {area_class} glaciers for leakage-safe splits, found {count}")
        class_options = []
        for val_id, test_id in itertools.permutations(ids, 2):
            class_options.append(
                {
                    glacier_id: ("val" if glacier_id == val_id else "test" if glacier_id == test_id else "train")
                    for glacier_id in ids
                }
            )
        options_by_class.append(class_options)

    workload = {
        str(row.glacier_id): float(row.task_count) * (1.0 + math.sqrt(max(float(row.area_km2), 0.0)))
        for row in unique.itertuples()
    }
    total_workload = sum(workload.values())
    targets = {"train": 0.60, "val": 0.20, "test": 0.20}
    best: tuple[float, str, dict[str, str]] | None = None
    for combination in itertools.product(*options_by_class):
        candidate = {key: value for option in combination for key, value in option.items()}
        totals = {
            split: sum(workload[glacier_id] for glacier_id, assigned in candidate.items() if assigned == split)
            for split in SPLIT_ORDER
        }
        score = sum((totals[split] / total_workload - targets[split]) ** 2 for split in SPLIT_ORDER)
        tie_breaker = stable_rank(json.dumps(candidate, sort_keys=True), seed)
        ranked = (score, tie_breaker, candidate)
        if best is None or ranked[:2] < best[:2]:
            best = ranked
    if best is None:
        raise ValueError("Unable to assign leakage-safe glacier splits")
    return best[2]


def axis_starts(low: float, high: float, size: int, stride: int, maximum: int, padding: int) -> list[int]:
    low_i = math.floor(low) - padding
    high_i = math.ceil(high) + padding
    if high_i - low_i <= size:
        starts = [(low_i + high_i - size) // 2]
    else:
        last = high_i - size
        starts = list(range(low_i, last + 1, stride))
        if not starts or starts[-1] != last:
            starts.append(last)
    return sorted({max(0, min(int(start), maximum - size)) for start in starts})


def windows_for_geometry(
    geometry,
    transform,
    *,
    width: int,
    height: int,
    patch_size: int,
    stride: int,
    padding: int,
) -> list[Window]:
    candidate = from_bounds(*geometry.bounds, transform=transform)
    rows = axis_starts(candidate.row_off, candidate.row_off + candidate.height, patch_size, stride, height, padding)
    cols = axis_starts(candidate.col_off, candidate.col_off + candidate.width, patch_size, stride, width, padding)
    return [Window(col, row, patch_size, patch_size) for row in rows for col in cols]


def normalize_window(raw: np.ma.MaskedArray) -> tuple[np.ndarray, np.ndarray]:
    data = np.asarray(raw.filled(0), dtype=np.float32)
    invalid = np.ma.getmaskarray(raw).any(axis=0)
    image = np.moveaxis(data, 0, -1)
    n_reflectance = min(len(config.S2_BANDS), image.shape[-1])
    reflectance = image[..., :n_reflectance]
    finite = reflectance[np.isfinite(reflectance)]
    scale = config.S2_SCALE if finite.size and float(np.max(np.abs(finite))) > 2.0 else 1.0
    image[..., :n_reflectance] = np.clip(reflectance / scale, 0.0, 1.0)
    if image.shape[-1] > n_reflectance:
        image[..., n_reflectance:] = np.clip(image[..., n_reflectance:], -1.0, 1.0)
    image = np.nan_to_num(image, nan=0.0, posinf=1.0, neginf=0.0)
    if image.shape[-1] == len(config.S2_BANDS):
        image = _append_sentinel2_indices(image)
    return image.astype(np.float32), ~invalid


def patch_weights(
    label: np.ndarray,
    review: np.ndarray,
    valid: np.ndarray,
    quality_score: float,
) -> np.ndarray:
    """Create explicit per-pixel reliability weights in [0, 1]."""
    quality = float(np.clip(quality_score / 100.0, 0.1, 1.0))
    weights = np.where(label > 0, 1.0, 0.45).astype(np.float32)
    weights[review > 0] *= 0.2
    weights *= quality
    weights[~valid] = 0.0
    return weights


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def render_qa_preview(
    output: Path,
    features_by_split: dict[str, list[np.ndarray]],
    labels_by_split: dict[str, list[np.ndarray]],
    weights_by_split: dict[str, list[np.ndarray]],
    metadata_by_split: dict[str, list[dict]],
) -> list[dict]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(3, 3, figsize=(12, 12), constrained_layout=True)
    cases: list[dict] = []
    for row_index, split in enumerate(SPLIT_ORDER):
        positive = np.asarray([item["positive_pixels"] for item in metadata_by_split[split]])
        selected = int(np.argsort(positive)[len(positive) // 2])
        image = features_by_split[split][selected].astype(np.float32)
        label = labels_by_split[split][selected]
        weights = weights_by_split[split][selected].astype(np.float32)
        rgb = image[..., [2, 1, 0]]
        low, high = np.percentile(rgb[np.isfinite(rgb)], [2, 98])
        rgb = np.clip((rgb - low) / max(high - low, 1e-6), 0, 1)
        metadata = metadata_by_split[split][selected]

        axes[row_index, 0].imshow(rgb)
        axes[row_index, 0].set_title(f"{split.upper()} · Sentinel-2 RGB")
        axes[row_index, 1].imshow(rgb)
        axes[row_index, 1].contour(label, levels=[0.5], colors=["#00f5ff"], linewidths=1.3)
        axes[row_index, 1].set_title(f"{metadata['glacier_id'].split('-')[-1]} · {metadata['year']} label")
        weight_image = axes[row_index, 2].imshow(weights, vmin=0, vmax=1, cmap="viridis")
        axes[row_index, 2].set_title("Pixel reliability weight")
        for axis in axes[row_index]:
            axis.set_axis_off()
        cases.append(
            {
                "split": split,
                "glacier_id": metadata["glacier_id"],
                "year": metadata["year"],
                "patch_index": selected,
            }
        )
    figure.colorbar(weight_image, ax=axes[:, 2], fraction=0.025, pad=0.02)
    figure.suptitle(
        "GlacierNET-KZ leakage-safe provisional training QA\n"
        "Cyan = provisional label; reliability is reduced in review/invalid zones",
        fontsize=14,
    )
    figure.savefig(output, dpi=170)
    plt.close(figure)
    return cases


def build(args: argparse.Namespace) -> Path:
    queue_path = ANNOTATION_DIR / "enhanced_annotation_queue.csv"
    annotation_manifest_path = ANNOTATION_DIR / "manifest.json"
    queue = pd.read_csv(queue_path)
    eligible = queue[queue["confidence"] == ELIGIBLE_CONFIDENCE].copy()
    if eligible.empty:
        raise ValueError("No high-provisional annotations are available")

    assignments = assign_glacier_splits(eligible, args.seed)
    eligible["split"] = eligible["glacier_id"].map(assignments)
    args.output.mkdir(parents=True, exist_ok=True)

    features_by_split: dict[str, list[np.ndarray]] = {split: [] for split in SPLIT_ORDER}
    labels_by_split: dict[str, list[np.ndarray]] = {split: [] for split in SPLIT_ORDER}
    weights_by_split: dict[str, list[np.ndarray]] = {split: [] for split in SPLIT_ORDER}
    metadata_by_split: dict[str, list[dict]] = {split: [] for split in SPLIT_ORDER}
    coverage_records: list[dict] = []

    for year in sorted(int(value) for value in eligible["year"].unique()):
        source_path = ROOT / f"data/raw/sentinel2/sentinel2_{year}.tif"
        gpkg_path = ANNOTATION_DIR / f"enhanced_labels_{year}.gpkg"
        labels = gpd.read_file(gpkg_path, layer="glacier_labels")
        reviews = gpd.read_file(gpkg_path, layer="review_zones").set_index("glacier_id")
        labels = labels[labels["confidence"] == ELIGIBLE_CONFIDENCE].copy()

        with rasterio.open(source_path) as source:
            if source.crs is None or source.count not in {len(config.S2_BANDS), config.N_CHANNELS}:
                raise ValueError(f"Unexpected source schema: {source_path}")
            if labels.crs != source.crs:
                labels = labels.to_crs(source.crs)
                reviews = reviews.to_crs(source.crs)

            for _, row in labels.sort_values("glacier_id").iterrows():
                glacier_id = str(row["glacier_id"])
                split = assignments[glacier_id]
                geometry = row.geometry
                review_geometry = reviews.loc[glacier_id].geometry
                windows = windows_for_geometry(
                    geometry,
                    source.transform,
                    width=source.width,
                    height=source.height,
                    patch_size=args.patch_size,
                    stride=args.stride,
                    padding=args.padding,
                )
                patch_footprints = []
                retained = 0
                for window in windows:
                    patch_transform = source.window_transform(window)
                    label = rasterize(
                        [(geometry, 1)],
                        out_shape=(args.patch_size, args.patch_size),
                        transform=patch_transform,
                        fill=0,
                        dtype=np.uint8,
                    )
                    positive_pixels = int(label.sum())
                    if positive_pixels < args.min_positive_pixels:
                        continue
                    review = rasterize(
                        [(review_geometry, 1)],
                        out_shape=(args.patch_size, args.patch_size),
                        transform=patch_transform,
                        fill=0,
                        dtype=np.uint8,
                    )
                    raw = source.read(window=window, boundless=True, masked=True, fill_value=0)
                    image, valid = normalize_window(raw)
                    if image.shape != (args.patch_size, args.patch_size, config.N_CHANNELS):
                        raise ValueError(f"Unexpected patch shape for {glacier_id}/{year}: {image.shape}")
                    weights = patch_weights(label, review, valid, float(row["quality_score"]))
                    if float(weights.mean()) <= 0:
                        continue

                    index = len(features_by_split[split])
                    features_by_split[split].append(image.astype(np.float16))
                    labels_by_split[split].append(label)
                    weights_by_split[split].append(weights.astype(np.float16))
                    left, bottom, right, top = rasterio.windows.bounds(window, source.transform)
                    patch_footprints.append(box(left, bottom, right, top))
                    metadata_by_split[split].append(
                        {
                            "patch_index": index,
                            "split": split,
                            "glacier_id": glacier_id,
                            "year": year,
                            "area_class": str(row["area_class"]),
                            "confidence": str(row["confidence"]),
                            "quality_score": float(row["quality_score"]),
                            "review_priority": int(row["review_priority"]),
                            "row_off": int(window.row_off),
                            "col_off": int(window.col_off),
                            "height": int(window.height),
                            "width": int(window.width),
                            "left": left,
                            "bottom": bottom,
                            "right": right,
                            "top": top,
                            "positive_pixels": positive_pixels,
                            "review_pixel_fraction": float(review.mean()),
                            "valid_pixel_fraction": float(valid.mean()),
                            "mean_training_weight": float(weights.mean()),
                            "source_file": relative(source_path),
                            "label_file": relative(gpkg_path),
                        }
                    )
                    retained += 1

                covered = geometry.intersection(unary_union(patch_footprints)).area if patch_footprints else 0.0
                coverage_records.append(
                    {
                        "glacier_id": glacier_id,
                        "year": year,
                        "split": split,
                        "patches": retained,
                        "geometry_coverage": float(covered / geometry.area) if geometry.area else 0.0,
                    }
                )

    outputs: list[dict] = []
    split_summary: dict[str, dict] = {}
    for split in SPLIT_ORDER:
        if not features_by_split[split]:
            raise ValueError(f"No patches generated for {split}")
        arrays = {
            f"X_{split}.npy": np.stack(features_by_split[split]).astype(np.float16),
            f"y_{split}.npy": np.stack(labels_by_split[split]).astype(np.uint8),
            f"w_{split}.npy": np.stack(weights_by_split[split]).astype(np.float16),
        }
        for name, array in arrays.items():
            path = args.output / name
            np.save(path, array)
            outputs.append({"path": relative(path), "sha256": sha256(path), "size_bytes": path.stat().st_size})
        meta_path = args.output / f"metadata_{split}.csv"
        pd.DataFrame(metadata_by_split[split]).to_csv(meta_path, index=False)
        outputs.append(
            {"path": relative(meta_path), "sha256": sha256(meta_path), "size_bytes": meta_path.stat().st_size}
        )
        split_summary[split] = {
            "glaciers": sorted(glacier_id for glacier_id, value in assignments.items() if value == split),
            "glacier_count": sum(value == split for value in assignments.values()),
            "patch_count": len(features_by_split[split]),
            "years": sorted({int(row["year"]) for row in metadata_by_split[split]}),
            "area_classes": dict(Counter(row["area_class"] for row in metadata_by_split[split])),
            "glacier_pixel_fraction": float(np.stack(labels_by_split[split]).mean()),
            "mean_training_weight": float(np.stack(weights_by_split[split]).mean()),
        }

    coverage_path = args.output / "coverage.csv"
    pd.DataFrame(coverage_records).to_csv(coverage_path, index=False)
    outputs.append(
        {"path": relative(coverage_path), "sha256": sha256(coverage_path), "size_bytes": coverage_path.stat().st_size}
    )
    qa_path = args.output / "training_qa_preview.png"
    qa_cases = render_qa_preview(
        qa_path,
        features_by_split,
        labels_by_split,
        weights_by_split,
        metadata_by_split,
    )
    outputs.append({"path": relative(qa_path), "sha256": sha256(qa_path), "size_bytes": qa_path.stat().st_size})

    annotation_manifest = json.loads(annotation_manifest_path.read_text(encoding="utf-8"))
    excluded = queue[queue["confidence"] != ELIGIBLE_CONFIDENCE]
    manifest = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_role": "machine_assisted_training_only_not_gold_benchmark",
        "annotation_status": "provisional_not_gold",
        "split_strategy": SPLIT_STRATEGY,
        "split_guarantee": "All years of each glacier are assigned to exactly one split.",
        "evaluation_limit": "Validation and test labels are provisional; metrics are internal development evidence only.",
        "seed": args.seed,
        "patch_size": args.patch_size,
        "stride": args.stride,
        "channel_count": config.N_CHANNELS,
        "feature_schema": config.ALL_BAND_NAMES,
        "feature_dtype": "float16",
        "label_dtype": "uint8",
        "weight_dtype": "float16",
        "eligible_confidence": ELIGIBLE_CONFIDENCE,
        "eligible_tasks": int(len(eligible)),
        "excluded_tasks": {
            "total": int(len(excluded)),
            "by_confidence": {str(key): int(value) for key, value in excluded["confidence"].value_counts().items()},
            "handling": "retained in active-review queue; never used as training truth",
        },
        "source_annotation_manifest": {
            "path": relative(annotation_manifest_path),
            "sha256": sha256(annotation_manifest_path),
            "label_tier": annotation_manifest["label_tier"],
        },
        "weight_policy": {
            "positive": 1.0,
            "background": 0.45,
            "review_zone_multiplier": 0.2,
            "quality_score_multiplier": "quality_score / 100",
            "invalid_pixels": 0.0,
        },
        "splits": split_summary,
        "coverage": {
            "records": len(coverage_records),
            "minimum_geometry_coverage": min(record["geometry_coverage"] for record in coverage_records),
        },
        "qa_preview": {"path": relative(qa_path), "cases": qa_cases},
        "outputs": outputs,
        "prohibited_claims": annotation_manifest["prohibited_claims"],
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Built {sum(value['patch_count'] for value in split_summary.values())} patches from "
        f"{len(assignments)} glaciers -> {manifest_path}"
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--patch-size", type=int, default=config.PATCH_SIZE)
    parser.add_argument("--stride", type=int, default=config.PATCH_SIZE // 2)
    parser.add_argument("--padding", type=int, default=32)
    parser.add_argument("--min-positive-pixels", type=int, default=64)
    parser.add_argument("--seed", type=int, default=config.RANDOM_SEED)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.patch_size != config.PATCH_SIZE:
        raise ValueError(f"patch-size must match configured model input: {config.PATCH_SIZE}")
    if not 1 <= args.stride <= args.patch_size:
        raise ValueError("stride must be in [1, patch-size]")
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
