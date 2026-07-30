"""Glacier-first orchestration for the deployable multimodal segmentation model.

The generic upload endpoint remains useful for arbitrary scenes.  This service
turns the local research assets into a reproducible product workflow:

RGI glacier + local year -> bounded source crop -> multimodal inference ->
glacier-specific evidence package.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import HTTPException

from app.config import RESULTS_DIR
from app.services.glacier_registry_service import get_glacier
from app.services.model_availability import is_model_available
from app.services.segmentation_service import run_segmentation
from app.utils import path_to_url
from src.inventory_guided_decoding import (
    InventoryGuidedDecoderConfig,
    inventory_guided_decode,
    normalized_difference,
)
from src.model_registry import MODEL_SPECS, get_model_spec, model_metadata
from src.model_security import verify_trusted_model


def _resolve_ml_core_dir() -> Path:
    """Ignore stale CORE_DIR values that do not contain the physical ML stack."""
    configured = Path(os.environ["CORE_DIR"]) if os.environ.get("CORE_DIR") else None
    repository = Path(__file__).resolve().parents[3]
    for candidate in (configured, repository):
        if candidate is not None and (candidate / "data" / "raw" / "sentinel2").is_dir():
            return candidate
    return repository


CORE_DIR = _resolve_ml_core_dir()
SENTINEL2_DIR = CORE_DIR / "data" / "raw" / "sentinel2"
TERRAIN_PATH = CORE_DIR / "data" / "ancillary" / "terrain" / "terrain_features.tif"
SENTINEL1_DIR = CORE_DIR / "data" / "ancillary" / "sentinel1"
CASES_DIR = RESULTS_DIR / "ml_cases"
CASES_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_DATASET_DIR = CORE_DIR / "data" / "processed" / "patches" / "enhanced_provisional_spatial_holdout"
TRAINING_DATASET_MANIFEST = TRAINING_DATASET_DIR / "manifest.json"
TRAINING_DATASET_PREVIEW = TRAINING_DATASET_DIR / "training_qa_preview.png"
SPATIAL_EVALUATION_REPORT = CORE_DIR / "results" / "enhanced_provisional_spatial_holdout_evaluation.json"
SPATIAL_MODEL_DIR = CORE_DIR / "models" / "unet_enhanced_provisional_spatial_holdout"
ANNOTATION_QUEUE = (
    CORE_DIR / "benchmarks" / "v2" / "annotations" / "enhanced_provisional" / "enhanced_annotation_queue.csv"
)
TRAINING_CHECK_DIR = RESULTS_DIR / "ml_training_checks"
TRAINING_CHECK_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_CHECK_RESULT = TRAINING_CHECK_DIR / "latest.json"
_TRAINING_CHECK_LOCK = threading.Lock()

SUPPORTED_MODELS = ("temporal_s2_terrain_s1", "temporal_s2_terrain")
PATCH_SIZE = 256
DEFAULT_CONTEXT_M = 400
MAX_WINDOW_PIXELS = 1280
INVENTORY_GUIDED_CONFIG = InventoryGuidedDecoderConfig()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"


def _review_action(flags: list[str]) -> str:
    if "empty_candidate" in flags:
        return "Inspect the source composite and redraw the glacier candidate; no training mask was accepted."
    if "temporal_disagreement" in flags:
        return "Compare 2022–2024 side by side and resolve the unstable boundary before promotion."
    if "low_rgi_iou" in flags or "very_low_rgi_iou" in flags:
        return "Inspect the RGI disagreement sector and retain only image-supported glacier geometry."
    if "large_review_zone" in flags:
        return "Review the highlighted boundary zone at full Sentinel-2 resolution."
    return "Perform a visual boundary review before this task can enter training."


def _annotation_review_queue(limit: int = 8) -> list[dict[str, Any]]:
    if not ANNOTATION_QUEUE.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with ANNOTATION_QUEUE.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("confidence") == "high_provisional":
                    continue
                flags = [value for value in str(row.get("flags", "")).split("|") if value]
                rows.append(
                    {
                        "glacier_id": str(row.get("glacier_id", "")),
                        "year": int(row.get("year", 0)),
                        "confidence": str(row.get("confidence", "")),
                        "quality_score": float(row.get("quality_score", 0)),
                        "review_priority": int(float(row.get("review_priority", 0))),
                        "flags": flags,
                        "next_action": _review_action(flags),
                    }
                )
    except (OSError, TypeError, ValueError):
        return []
    rows.sort(key=lambda item: (-item["review_priority"], item["quality_score"], item["glacier_id"], item["year"]))
    return rows[:limit]


def _spatial_evaluation_summary() -> dict[str, Any]:
    """Return bounded evidence from the glacier-disjoint development test."""
    report = _json(SPATIAL_EVALUATION_REPORT)
    baseline = report.get("baseline_before_finetuning", {})
    candidate = report.get("candidate_after_finetuning", {})
    training = report.get("training", {})
    dataset = report.get("dataset", {})
    if report.get("schema") != "glaciernet-kz.enhanced-spatial-evaluation.v1":
        return {
            "status": "not_run",
            "reason": "No compatible glacier-group spatial evaluation report is available.",
        }

    model_present = SPATIAL_MODEL_DIR.is_dir() and any(SPATIAL_MODEL_DIR.iterdir())
    return {
        "status": report.get("status"),
        "created_at": report.get("created_at"),
        "claim_scope": report.get("claim_scope"),
        "annotation_status": dataset.get("annotation_status"),
        "split_strategy": dataset.get("split_strategy"),
        "patches": dataset.get("patches", {}),
        "glacier_counts": {
            split: len(values) for split, values in dataset.get("glaciers", {}).items() if isinstance(values, list)
        },
        "epochs_requested": training.get("epochs_requested"),
        "epochs_completed": training.get("epochs_completed"),
        "baseline_test": baseline.get("test_metrics", {}),
        "candidate_test": candidate.get("test_metrics", {}),
        "candidate_minus_baseline_hard_iou": report.get("candidate_minus_baseline_test_hard_iou"),
        "promotion": report.get("promotion", {}),
        "model_artifact_present": model_present,
        "claims_allowed": report.get("claims_allowed", []),
        "claims_not_allowed": report.get("claims_not_allowed", []),
        "limitations": [
            "Only two glaciers are present in the untouched internal test split.",
            "Labels are machine-assisted provisional labels, not independently adjudicated gold labels.",
            "This result does not establish external-regional or operational hazard performance.",
        ],
    }


def training_dataset_readiness() -> dict[str, Any]:
    """Expose a bounded, claim-safe summary of the weighted annotation export."""
    manifest = _json(TRAINING_DATASET_MANIFEST)
    if not manifest:
        return {
            "status": "blocked",
            "dataset_id": "enhanced_provisional_spatial_holdout",
            "reason": "The local leakage-safe training manifest is missing or unreadable.",
            "preview_url": None,
            "manifest_url": "/api/ml/training-dataset",
            "splits": {},
            "membership": {},
            "review_queue": [],
            "spatial_evaluation": _spatial_evaluation_summary(),
            "limitations": [
                "No model training or accuracy claim is available from a missing dataset.",
            ],
        }

    required = [
        TRAINING_DATASET_DIR / f"{prefix}_{split}.npy"
        for split in ("train", "val", "test")
        for prefix in ("X", "y", "w")
    ]
    declared_outputs = manifest.get("outputs", [])
    outputs_complete = bool(declared_outputs) and all(
        (CORE_DIR / str(item.get("path", ""))).is_file()
        and (CORE_DIR / str(item.get("path", ""))).stat().st_size == int(item.get("size_bytes", -1))
        for item in declared_outputs
    )
    structurally_ready = (
        manifest.get("schema") == "glaciernet-kz.enhanced-provisional-training.v1"
        and manifest.get("annotation_status") == "provisional_not_gold"
        and manifest.get("split_strategy") == "glacier_group_spatial_holdout"
        and all(path.is_file() for path in required)
        and outputs_complete
        and TRAINING_DATASET_PREVIEW.is_file()
    )
    splits: dict[str, Any] = {}
    membership: dict[str, str] = {}
    for split in ("train", "val", "test"):
        source = manifest.get("splits", {}).get(split, {})
        glaciers = [str(value) for value in source.get("glaciers", [])]
        splits[split] = {
            "patch_count": int(source.get("patch_count", 0)),
            "glacier_count": int(source.get("glacier_count", len(glaciers))),
            "glaciers": glaciers,
            "years": [int(value) for value in source.get("years", [])],
            "glacier_pixel_fraction": source.get("glacier_pixel_fraction"),
            "mean_training_weight": source.get("mean_training_weight"),
        }
        membership.update({glacier_id: split for glacier_id in glaciers})

    coverage = manifest.get("coverage", {})
    excluded = manifest.get("excluded_tasks", {})
    return {
        "status": "ready" if structurally_ready else "blocked",
        "dataset_id": "enhanced_provisional_spatial_holdout",
        "schema": manifest.get("schema"),
        "created_at": manifest.get("created_at"),
        "annotation_status": manifest.get("annotation_status"),
        "dataset_role": manifest.get("dataset_role"),
        "split_strategy": manifest.get("split_strategy"),
        "channel_count": int(manifest.get("channel_count", 0)),
        "patch_size": int(manifest.get("patch_size", 0)),
        "feature_schema": manifest.get("feature_schema", []),
        "eligible_tasks": int(manifest.get("eligible_tasks", 0)),
        "patch_count": sum(item["patch_count"] for item in splits.values()),
        "storage_bytes": sum(path.stat().st_size for path in required if path.is_file()),
        "minimum_geometry_coverage": coverage.get("minimum_geometry_coverage"),
        "excluded_tasks": {
            "total": int(excluded.get("total", 0)),
            "by_confidence": excluded.get("by_confidence", {}),
            "handling": excluded.get("handling"),
        },
        "splits": splits,
        "membership": membership,
        "review_queue": _annotation_review_queue(),
        "spatial_evaluation": _spatial_evaluation_summary(),
        "weight_policy": manifest.get("weight_policy", {}),
        "preview_url": "/api/ml/training-dataset/preview" if TRAINING_DATASET_PREVIEW.is_file() else None,
        "manifest_url": "/api/ml/training-dataset",
        "rebuild_command": (
            "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python "
            "scripts/build_enhanced_provisional_training_dataset.py"
        ),
        "validation_command": (
            "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python "
            "scripts/validate_enhanced_provisional_training_dataset.py"
        ),
        "training_command": (
            "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python "
            "scripts/train_enhanced_spatial_holdout.py --epochs 40 --batch-size 2 --learning-rate 1e-5"
        ),
        "integrity": {
            "required_arrays_present": all(path.is_file() for path in required),
            "declared_outputs_size_matched": outputs_complete,
            "full_sha256_validation": "enforced by scripts/validate_enhanced_provisional_training_dataset.py",
        },
        "limitations": [
            "The labels are machine-assisted provisional labels, not independently adjudicated gold labels.",
            "Validation and test metrics are internal model-development evidence only.",
            "Medium and low confidence tasks remain in the review queue and are not training truth.",
        ],
    }


def verify_weighted_training_pipeline(*, refresh: bool = False) -> dict[str, Any]:
    """Run one real, bounded TensorFlow update to prove weighted data compatibility."""
    readiness = training_dataset_readiness()
    if readiness.get("status") != "ready":
        raise HTTPException(409, readiness.get("reason") or "Weighted training dataset is not ready")

    manifest_sha = _sha256(TRAINING_DATASET_MANIFEST)
    cached = _json(TRAINING_CHECK_RESULT)
    if not refresh and cached.get("status") == "verified" and cached.get("dataset_manifest_sha256") == manifest_sha:
        return {**cached, "cache": {"hit": True}}
    if not _TRAINING_CHECK_LOCK.acquire(blocking=False):
        raise HTTPException(409, "A weighted training pipeline check is already running")

    started = time.perf_counter()
    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        import tensorflow as tf

        from src.models import build_data_generator, build_model_by_name, compile_model

        x = np.load(TRAINING_DATASET_DIR / "X_train.npy", mmap_mode="r")
        y = np.load(TRAINING_DATASET_DIR / "y_train.npy", mmap_mode="r")
        weights = np.load(TRAINING_DATASET_DIR / "w_train.npy", mmap_mode="r")
        if x.shape[0] < 1 or y.shape != x.shape[:3] or weights.shape != y.shape:
            raise HTTPException(409, "Weighted training arrays are empty or misaligned")

        tf.keras.backend.clear_session()
        tf.keras.utils.set_random_seed(42)
        generator_class = build_data_generator()
        generator = generator_class(
            x,
            y,
            sample_weights=weights,
            batch_size=1,
            augment=True,
            shuffle=False,
            seed=42,
        )
        x_batch, y_batch, weight_batch = generator[0]
        model = compile_model(
            build_model_by_name("unet", tuple(int(value) for value in x_batch.shape[1:])),
            learning_rate=1e-4,
            use_focal=False,
        )
        metrics = model.train_on_batch(
            x_batch,
            y_batch,
            sample_weight=weight_batch,
            return_dict=True,
        )
        result = {
            "schema": "glaciernet-kz.weighted-training-check.v1",
            "status": "verified",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "dataset_id": readiness["dataset_id"],
            "dataset_manifest_sha256": manifest_sha,
            "purpose": "Pipeline compatibility check; one batch is not model training or accuracy evidence.",
            "architecture": "unet",
            "batch": {
                "features": [int(value) for value in x_batch.shape],
                "labels": [int(value) for value in y_batch.shape],
                "weights": [int(value) for value in weight_batch.shape],
                "weight_min": float(weight_batch.min()),
                "weight_max": float(weight_batch.max()),
                "nonzero_weight_fraction": float((weight_batch > 0).mean()),
            },
            "metrics": {str(key): float(value) for key, value in metrics.items()},
            "runtime": {
                "duration_seconds": round(time.perf_counter() - started, 3),
                "tensorflow": tf.__version__,
                "python": platform.python_version(),
                "devices": [device.device_type for device in tf.config.list_physical_devices()],
            },
            "claims_allowed": [
                "The weighted dataset can execute a real TensorFlow optimization step.",
                "Pixel reliability maps are accepted by the segmentation loss pipeline.",
            ],
            "claims_not_allowed": [
                "The model is trained after one batch.",
                "The returned batch metrics estimate independent segmentation accuracy.",
            ],
            "cache": {"hit": False},
        }
        temporary = TRAINING_CHECK_RESULT.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        temporary.replace(TRAINING_CHECK_RESULT)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Weighted TensorFlow pipeline check failed: {exc}") from exc
    finally:
        try:
            import tensorflow as tf

            tf.keras.backend.clear_session()
        except Exception:
            pass
        _TRAINING_CHECK_LOCK.release()


def _available_years() -> list[dict[str, Any]]:
    years: list[dict[str, Any]] = []
    for source in sorted(SENTINEL2_DIR.glob("sentinel2_*.tif")):
        try:
            year = int(source.stem.rsplit("_", 1)[-1])
        except ValueError:
            continue
        terrain = TERRAIN_PATH.is_file()
        sar = (SENTINEL1_DIR / f"sentinel1_{year}.tif").is_file()
        compatible = [
            name
            for name in SUPPORTED_MODELS
            if is_model_available(name)
            and (MODEL_SPECS[name].year_min or year) <= year <= (MODEL_SPECS[name].year_max or year)
            and (name != "temporal_s2_terrain_s1" or sar)
            and terrain
        ]
        years.append(
            {
                "year": year,
                "sentinel2": True,
                "terrain": terrain,
                "sentinel1": sar,
                "compatible_models": compatible,
                "recommended_model": compatible[0] if compatible else None,
            }
        )
    return years


def ml_readiness() -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    for name in SUPPORTED_MODELS:
        spec = get_model_spec(name)
        report = _json(spec.report_path(CORE_DIR) or Path())
        hard = report.get("threshold_calibration", {}).get("selected_metrics", {})
        artifact = spec.artifact_path(CORE_DIR)
        trusted = False
        if artifact and artifact.exists():
            try:
                verify_trusted_model(artifact, root=CORE_DIR)
                trusted = True
            except (FileNotFoundError, OSError, ValueError, KeyError):
                trusted = False
        models.append(
            {
                **model_metadata(spec, CORE_DIR),
                "available": is_model_available(name),
                "trusted_artifact": trusted,
                "benchmark": {
                    "protocol": report.get("evaluation_protocol"),
                    "test_years": report.get("test_years", []),
                    "hard_dice": hard.get("hard_dice"),
                    "hard_iou": hard.get("hard_iou"),
                    "precision": hard.get("precision"),
                    "recall": hard.get("recall"),
                    "area_bias_percent": hard.get("area_bias_percent"),
                    "label_quality_tier": report.get("label_quality_tier"),
                    "generalisation_scope": report.get("generalisation_scope"),
                },
            }
        )
    years = _available_years()
    ready_years = [item["year"] for item in years if item["compatible_models"]]
    safeguard_report = _json(CORE_DIR / "benchmarks/v2/provisional/inventory_guided_decoder_2024.json")
    safeguard_replay = safeguard_report.get("external_replay", {})
    return {
        "status": "ready" if ready_years and any(item["available"] for item in models) else "blocked",
        "recommended_model": next(
            (item["name"] for item in models if item.get("recommended") and item["available"]), None
        ),
        "years": years,
        "models": models,
        "training_dataset": training_dataset_readiness(),
        "generalisation_sentinel": {
            "status": safeguard_report.get("status", "unavailable"),
            "selected_config": safeguard_report.get("selection_protocol", {}).get("selected_config"),
            "n_external_glaciers": safeguard_replay.get("n_glaciers"),
            "baseline_hard_dice": safeguard_replay.get("unconstrained_model_baseline", {})
            .get("hard_dice", {})
            .get("estimate"),
            "safeguard_hard_dice": safeguard_replay.get("metrics_bootstrap", {}).get("hard_dice", {}).get("estimate"),
            "paired_dice_delta": safeguard_replay.get("paired_delta_decoder_minus_unconstrained_model", {})
            .get("hard_dice", {})
            .get("estimate"),
            "claim_tier": "provisional_inventory_guided_failure_containment",
        },
        "workflow": [
            "Select a glacier from the physical RGI 7.0 registry.",
            "Select a locally available Sentinel-2 year.",
            "Run the compatible temporal model with aligned terrain and Sentinel-1 features.",
            "Review the model boundary, probability, entropy and inventory disagreement.",
            "Compare the unconstrained ML boundary with the physics-constrained Generalisation Sentinel candidate.",
            "Open the same glacier-year case in Risk Twin or download the audit manifest.",
        ],
        "interpretation": (
            "Model outputs are screening evidence. RGI overlap measures agreement with an "
            "inventory boundary, not independent accuracy."
        ),
    }


def _analysis_key(rgi_id: str, year: int, model_name: str, use_tta: bool, context_m: int) -> str:
    source = SENTINEL2_DIR / f"sentinel2_{year}.tif"
    spec = get_model_spec(model_name)
    report = _json(spec.report_path(CORE_DIR) or Path())
    payload = {
        "schema": "glaciernet-kz.ml-case.v1",
        "rgi_id": rgi_id,
        "year": year,
        "model": model_name,
        "tta": use_tta,
        "context_m": context_m,
        "source": _source_fingerprint(source),
        "model_sha256": report.get("model_artifact_sha256"),
        "inventory_guided_decoder": INVENTORY_GUIDED_CONFIG.to_dict(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def _bounded_window(source, geometry: dict[str, Any], context_m: int):
    from rasterio.features import bounds as geometry_bounds
    from rasterio.warp import transform_geom
    from rasterio.windows import Window, from_bounds

    projected = transform_geom("EPSG:4326", source.crs, geometry, precision=3)
    left, bottom, right, top = geometry_bounds(projected)
    left -= context_m
    bottom -= context_m
    right += context_m
    top += context_m
    raw = from_bounds(left, bottom, right, top, source.transform)
    width = max(PATCH_SIZE, int(math.ceil(raw.width / PATCH_SIZE) * PATCH_SIZE))
    height = max(PATCH_SIZE, int(math.ceil(raw.height / PATCH_SIZE) * PATCH_SIZE))
    if width > MAX_WINDOW_PIXELS or height > MAX_WINDOW_PIXELS:
        raise HTTPException(
            422,
            f"Glacier analysis window {width}x{height} exceeds the safe "
            f"{MAX_WINDOW_PIXELS}px limit. Reduce context_m for this exceptionally large glacier.",
        )
    center_col = raw.col_off + raw.width / 2
    center_row = raw.row_off + raw.height / 2
    col_off = int(round(center_col - width / 2))
    row_off = int(round(center_row - height / 2))
    col_off = min(max(0, col_off), max(0, source.width - width))
    row_off = min(max(0, row_off), max(0, source.height - height))
    window = Window(col_off, row_off, min(width, source.width), min(height, source.height))
    if window.width < PATCH_SIZE or window.height < PATCH_SIZE:
        raise HTTPException(422, "The glacier is outside the usable local Sentinel-2 footprint")
    return window, projected


def _write_source_crop(source_path: Path, geometry: dict[str, Any], target: Path, context_m: int) -> dict[str, Any]:
    import rasterio

    with rasterio.open(source_path) as source:
        if source.crs is None:
            raise HTTPException(422, f"{source_path.name} has no CRS")
        window, projected = _bounded_window(source, geometry, context_m)
        data = source.read(window=window)
        transform = source.window_transform(window)
        profile = source.profile.copy()
        profile.update(
            height=int(window.height),
            width=int(window.width),
            transform=transform,
            compress="deflate",
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(target, "w", **profile) as destination:
            destination.write(data)
            for index, description in enumerate(source.descriptions, start=1):
                if description:
                    destination.set_band_description(index, description)
        return {
            "shape": [int(window.height), int(window.width)],
            "transform": transform,
            "crs": source.crs,
            "projected_geometry": projected,
            "bounds": rasterio.windows.bounds(window, source.transform),
        }


def _move_artifact(path_value: str | None, case_dir: Path, label: str) -> Path | None:
    if not path_value:
        return None
    source = Path(path_value)
    if not source.is_file():
        return None
    destination = case_dir / f"{label}{source.suffix}"
    if source.resolve() != destination.resolve():
        shutil.move(str(source), str(destination))
    return destination


def _geojson_and_metrics(
    *,
    source_crop_path: Path,
    mask_path: Path,
    probability_path: Path,
    entropy_path: Path,
    geometry_wgs84: dict[str, Any],
    case_dir: Path,
) -> dict[str, Any]:
    import rasterio
    from rasterio.features import rasterize, shapes
    from rasterio.warp import transform_geom
    from scipy import ndimage
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    with rasterio.open(mask_path) as source:
        predicted = source.read(1) > 0
        profile = source.profile.copy()
        projected = transform_geom("EPSG:4326", source.crs, geometry_wgs84, precision=3)
        reference = rasterize(
            [(projected, 1)],
            out_shape=predicted.shape,
            transform=source.transform,
            fill=0,
            dtype="uint8",
        ).astype(bool)
        labels, _ = ndimage.label(predicted)
        overlapping_labels = np.unique(labels[reference & predicted])
        overlapping_labels = overlapping_labels[overlapping_labels > 0]
        selected = np.isin(labels, overlapping_labels) if overlapping_labels.size else np.zeros_like(predicted)
        pixel_area_m2 = abs(source.transform.a * source.transform.e - source.transform.b * source.transform.d)

        selected_path = case_dir / "selected_glacier_mask.tif"
        profile.update(dtype="uint8", count=1, compress="deflate")
        with rasterio.open(selected_path, "w", **profile) as destination:
            destination.write(selected.astype("uint8"), 1)
            destination.set_band_description(1, "selected_glacier_component")

        with rasterio.open(source_crop_path) as crop_source:
            if crop_source.count < 6 or (crop_source.height, crop_source.width) != predicted.shape:
                raise ValueError("source crop is incompatible with inventory-guided decoding")
            green = crop_source.read(2).astype(np.float32)
            swir = crop_source.read(6).astype(np.float32)
        guided_mask, guided_diagnostics = inventory_guided_decode(
            normalized_difference(green, swir),
            reference,
            pixel_size_m=float(np.sqrt(pixel_area_m2)),
            config=INVENTORY_GUIDED_CONFIG,
        )
        guided = guided_mask.astype(bool)
        guided_path = case_dir / "inventory_guided_mask.tif"
        with rasterio.open(guided_path, "w", **profile) as destination:
            destination.write(guided_mask, 1)
            destination.set_band_description(1, "inventory_guided_spectral_candidate")

        polygon_parts = [
            shape(value)
            for value, value_id in shapes(selected.astype("uint8"), mask=selected, transform=source.transform)
            if int(value_id) == 1
        ]
        if polygon_parts:
            combined = unary_union(polygon_parts).simplify(max(abs(source.transform.a), abs(source.transform.e)))
            model_geometry = transform_geom(source.crs, "EPSG:4326", mapping(combined), precision=7)
        else:
            model_geometry = None
        guided_parts = [
            shape(value)
            for value, value_id in shapes(guided_mask, mask=guided, transform=source.transform)
            if int(value_id) == 1
        ]
        if guided_parts:
            combined_guided = unary_union(guided_parts).simplify(max(abs(source.transform.a), abs(source.transform.e)))
            guided_geometry = transform_geom(source.crs, "EPSG:4326", mapping(combined_guided), precision=7)
        else:
            guided_geometry = None
        bounds_projected = source.bounds
        bounds_wgs84_geom = transform_geom(
            source.crs,
            "EPSG:4326",
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [bounds_projected.left, bounds_projected.bottom],
                        [bounds_projected.right, bounds_projected.bottom],
                        [bounds_projected.right, bounds_projected.top],
                        [bounds_projected.left, bounds_projected.top],
                        [bounds_projected.left, bounds_projected.bottom],
                    ]
                ],
            },
            precision=7,
        )
        bounds_coords = np.asarray(bounds_wgs84_geom["coordinates"][0], dtype=float)
        map_bounds = [
            [float(bounds_coords[:, 1].min()), float(bounds_coords[:, 0].min())],
            [float(bounds_coords[:, 1].max()), float(bounds_coords[:, 0].max())],
        ]

    with rasterio.open(probability_path) as source:
        probability = source.read(1)
    with rasterio.open(entropy_path) as source:
        entropy = source.read(1)

    intersection = int(np.count_nonzero(selected & reference))
    union = int(np.count_nonzero(selected | reference))
    predicted_pixels = int(np.count_nonzero(selected))
    reference_pixels = int(np.count_nonzero(reference))
    predicted_area = predicted_pixels * pixel_area_m2 / 1_000_000
    guided_pixels = int(np.count_nonzero(guided))
    guided_area = guided_pixels * pixel_area_m2 / 1_000_000
    reference_area = reference_pixels * pixel_area_m2 / 1_000_000
    overlap_iou = intersection / union if union else 0.0
    guided_intersection = int(np.count_nonzero(guided & reference))
    guided_union = int(np.count_nonzero(guided | reference))
    guided_iou = guided_intersection / guided_union if guided_union else 0.0
    area_delta_percent = (predicted_area - reference_area) / reference_area * 100 if reference_area else None
    guided_area_delta_percent = (guided_area - reference_area) / reference_area * 100 if reference_area else None
    boundary = ndimage.binary_dilation(selected | reference, iterations=2) ^ ndimage.binary_erosion(
        selected | reference, iterations=2
    )
    review_zone = selected | reference
    uncertain = entropy > 0.65
    uncertain_fraction = float(np.mean(uncertain[review_zone])) if np.any(review_zone) else 1.0
    boundary_uncertainty = float(np.mean(entropy[boundary])) if np.any(boundary) else None
    mean_probability = float(np.mean(probability[selected])) if np.any(selected) else 0.0
    disagreement = 1.0 - overlap_iou
    priority = int(round(min(100.0, 20.0 + 50.0 * disagreement + 30.0 * uncertain_fraction)))

    feature = {
        "type": "Feature",
        "properties": {
            "source": "GlacierNET-KZ temporal segmentation",
            "interpretation": "model screening boundary; not independently adjudicated",
        },
        "geometry": model_geometry,
    }
    boundary_path = case_dir / "model_boundary.geojson"
    boundary_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": [feature] if model_geometry else []}),
        encoding="utf-8",
    )
    return {
        "model_geometry": model_geometry,
        "inventory_guided_geometry": guided_geometry,
        "boundary_path": boundary_path,
        "selected_mask_path": selected_path,
        "inventory_guided_mask_path": guided_path,
        "map_bounds": map_bounds,
        "metrics": {
            "predicted_area_km2": round(predicted_area, 4),
            "rgi_rasterized_area_km2": round(reference_area, 4),
            "area_delta_percent": round(area_delta_percent, 2) if area_delta_percent is not None else None,
            "rgi_overlap_iou": round(overlap_iou, 4),
            "mean_probability_in_selected_component": round(mean_probability, 4),
            "uncertain_fraction_in_review_zone": round(uncertain_fraction, 4),
            "mean_boundary_entropy_nats": round(boundary_uncertainty, 4) if boundary_uncertainty is not None else None,
            "review_priority_0_100": priority,
            "inventory_guided_area_km2": round(guided_area, 4),
            "inventory_guided_area_delta_percent": (
                round(guided_area_delta_percent, 2) if guided_area_delta_percent is not None else None
            ),
            "inventory_guided_rgi_overlap_iou": round(guided_iou, 4),
            "inventory_guided_spectral_fraction": round(
                float(guided_diagnostics["inventory_spectral_fraction"]),
                4,
            ),
        },
        "inventory_guided_decoder": guided_diagnostics,
    }


def _hydrate_urls(case: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    hydrated = json.loads(json.dumps(case))
    for key, value in list(hydrated.get("artifacts", {}).items()):
        if key.endswith("_path") and value:
            hydrated["artifacts"][key.replace("_path", "_url")] = path_to_url(value)
    hydrated["artifacts"]["manifest_url"] = path_to_url(manifest_path)
    return hydrated


def analyze_glacier(
    rgi_id: str,
    *,
    year: int,
    model_name: str = "temporal_s2_terrain_s1",
    use_tta: bool = True,
    context_m: int = DEFAULT_CONTEXT_M,
    refresh: bool = False,
) -> dict[str, Any]:
    if model_name not in SUPPORTED_MODELS:
        raise HTTPException(400, f"model_name must be one of: {', '.join(SUPPORTED_MODELS)}")
    if not 0 <= context_m <= 2000:
        raise HTTPException(400, "context_m must be between 0 and 2000")
    spec = get_model_spec(model_name)
    if spec.year_min is not None and not spec.year_min <= year <= (spec.year_max or year):
        raise HTTPException(422, f"{model_name} is supported only for {spec.year_min}–{spec.year_max}")
    source_path = SENTINEL2_DIR / f"sentinel2_{year}.tif"
    if not source_path.is_file():
        raise HTTPException(404, f"Local Sentinel-2 source is missing for {year}")
    if not is_model_available(model_name):
        raise HTTPException(503, f"Trusted deployable artifact is unavailable for {model_name}")
    if model_name == "temporal_s2_terrain_s1" and not (SENTINEL1_DIR / f"sentinel1_{year}.tif").is_file():
        raise HTTPException(422, f"Local Sentinel-1 composite is missing for {year}")

    case_id = _analysis_key(rgi_id, year, model_name, use_tta, context_m)
    case_dir = CASES_DIR / case_id
    manifest_path = case_dir / "manifest.json"
    if manifest_path.is_file() and not refresh:
        cached = _json(manifest_path)
        if cached:
            cached["cache"] = {"hit": True, "case_id": case_id}
            return _hydrate_urls(cached, manifest_path)

    glacier = get_glacier(rgi_id, include_geometry=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    crop_path = case_dir / "source_crop.tif"
    started = time.perf_counter()
    crop = _write_source_crop(source_path, glacier["geometry"], crop_path, context_m)
    crop_sha256 = _sha256(crop_path)
    result = run_segmentation(
        crop_path,
        model_name=model_name,
        use_tta=use_tta,
        use_crf=False,
        year=year,
    )
    if result.get("status") != "completed":
        crop_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Segmentation failed: {result.get('error', 'unknown error')}")

    moved = {
        "mask_path": _move_artifact(result.get("geotiff_path"), case_dir, "model_mask"),
        "mask_preview_path": _move_artifact(result.get("mask_path"), case_dir, "model_mask"),
        "overlay_path": _move_artifact(result.get("overlay_path"), case_dir, "model_overlay"),
        "probability_path": _move_artifact(result.get("probability_geotiff_path"), case_dir, "probability"),
        "probability_preview_path": _move_artifact(result.get("probability_path"), case_dir, "probability"),
        "entropy_path": _move_artifact(result.get("entropy_geotiff_path"), case_dir, "entropy"),
        "entropy_preview_path": _move_artifact(result.get("entropy_path"), case_dir, "entropy"),
    }
    required = ("mask_path", "probability_path", "entropy_path")
    if any(moved[key] is None for key in required):
        raise HTTPException(500, "Inference did not produce the required geospatial evidence layers")

    evidence = _geojson_and_metrics(
        source_crop_path=crop_path,
        mask_path=moved["mask_path"],
        probability_path=moved["probability_path"],
        entropy_path=moved["entropy_path"],
        geometry_wgs84=glacier["geometry"],
        case_dir=case_dir,
    )
    moved["selected_mask_path"] = evidence["selected_mask_path"]
    moved["inventory_guided_mask_path"] = evidence["inventory_guided_mask_path"]
    moved["boundary_path"] = evidence["boundary_path"]
    crop_path.unlink(missing_ok=True)

    report = _json(spec.report_path(CORE_DIR) or Path())
    elapsed = time.perf_counter() - started
    case = {
        "schema": "glaciernet-kz.ml-case.v1",
        "case_id": case_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "glacier": glacier,
        "year": year,
        "model": {
            **model_metadata(spec, CORE_DIR),
            "artifact_sha256": report.get("model_artifact_sha256"),
            "benchmark_protocol": report.get("evaluation_protocol"),
            "test_years": report.get("test_years", []),
            "label_quality_tier": report.get("label_quality_tier"),
        },
        "inference": {
            "variant": result.get("inference_variant"),
            "use_tta": use_tta,
            "decision_threshold": result.get("decision_threshold"),
            "duration_seconds": round(elapsed, 3),
            "window_shape": crop["shape"],
            "context_m": context_m,
            "feature_schema": result.get("feature_schema", []),
        },
        "source": {
            "sentinel2_file": str(source_path.relative_to(CORE_DIR)),
            "sentinel2_size_bytes": source_path.stat().st_size,
            "source_crop_sha256": crop_sha256,
            "terrain_file": str(TERRAIN_PATH.relative_to(CORE_DIR)),
            "sentinel1_file": str((SENTINEL1_DIR / f"sentinel1_{year}.tif").relative_to(CORE_DIR))
            if model_name == "temporal_s2_terrain_s1"
            else None,
        },
        "metrics": evidence["metrics"],
        "map": {
            "bounds": evidence["map_bounds"],
            "rgi_geometry": glacier["geometry"],
            "model_geometry": evidence["model_geometry"],
            "inventory_guided_geometry": evidence["inventory_guided_geometry"],
        },
        "inventory_guided_decoder": evidence["inventory_guided_decoder"],
        "artifacts": {key: str(value) if value else None for key, value in moved.items()},
        "review": {
            "status": "expert_review_required",
            "next_action": (
                "Inspect high-entropy boundary sectors and the largest RGI disagreement before "
                "using this boundary in a trend or hazard assessment."
            ),
            "risk_twin_url": (f"/risk-twin?rgi={rgi_id}&year={year}&scope=annual_screening&ml_case={case_id}"),
        },
        "claims_allowed": [
            "model-screened glacier boundary for the selected local year",
            "agreement and disagreement with the fixed RGI inventory geometry",
            "model probability and predictive-entropy review zones",
            "inventory-guided spectral candidate for failure containment and annotation review",
        ],
        "claims_not_allowed": [
            "independent expert-validated accuracy for this glacier",
            "ice thickness, volume or discharge inferred from a 2D boundary",
            "operational hazard probability or public warning",
        ],
        "warnings": result.get("warnings", []),
        "cache": {"hit": False, "case_id": case_id},
    }
    manifest_path.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
    return _hydrate_urls(case, manifest_path)


def get_ml_case(case_id: str) -> dict[str, Any]:
    if not case_id or any(character not in "0123456789abcdef" for character in case_id):
        raise HTTPException(400, "Invalid case_id")
    manifest_path = CASES_DIR / case_id / "manifest.json"
    case = _json(manifest_path)
    if not case:
        raise HTTPException(404, "ML evidence case not found")
    case["cache"] = {"hit": True, "case_id": case_id}
    return _hydrate_urls(case, manifest_path)


def list_ml_cases(limit: int = 20) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for manifest in sorted(CASES_DIR.glob("*/manifest.json"), key=os.path.getmtime, reverse=True):
        case = _json(manifest)
        if case:
            cases.append(
                {
                    "case_id": case.get("case_id"),
                    "created_at": case.get("created_at"),
                    "year": case.get("year"),
                    "glacier": {
                        key: case.get("glacier", {}).get(key) for key in ("rgi_id", "name", "name_ru", "rgi_area_km2")
                    },
                    "model_name": case.get("model", {}).get("name"),
                    "review_priority_0_100": case.get("metrics", {}).get("review_priority_0_100"),
                    "manifest_url": path_to_url(manifest),
                }
            )
        if len(cases) >= limit:
            break
    return {"cases": cases, "total_returned": len(cases)}
