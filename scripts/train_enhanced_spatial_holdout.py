#!/usr/bin/env python3
"""Fine-tune and evaluate the provisional glacier-group spatial holdout.

The test split is never used for training, early stopping, or threshold
selection. Metrics remain internal development evidence because the labels are
machine-assisted and provisional rather than independently adjudicated gold.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_metrics import (  # noqa: E402
    area_metrics,
    bootstrap_confidence_intervals,
    calibrate_threshold,
    hard_segmentation_metrics,
    probability_calibration_metrics,
)
from src.models import build_data_generator, compile_model, get_custom_objects  # noqa: E402
from src.provenance import sha256_directory  # noqa: E402

DEFAULT_DATASET = ROOT / "data/processed/patches/enhanced_provisional_spatial_holdout"
DEFAULT_INITIAL_MODEL = ROOT / "models/unet_best.h5"
DEFAULT_MODEL = ROOT / "models/unet_enhanced_provisional_spatial_holdout"
DEFAULT_REPORT = ROOT / "results/enhanced_provisional_spatial_holdout_evaluation.json"
DEFAULT_HISTORY = ROOT / "results/training_log_unet_enhanced_provisional_spatial_holdout.csv"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _metadata(path: Path, split: str, expected_count: int) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != expected_count:
        raise ValueError(f"{split} metadata rows {len(rows)} != array rows {expected_count}")
    indices = [int(row["patch_index"]) for row in rows]
    if indices != list(range(expected_count)):
        raise ValueError(f"{split} metadata patch_index must match array order")
    if any(row.get("split") != split for row in rows):
        raise ValueError(f"{split} metadata contains a different split")
    return rows


def validate_glacier_disjoint(rows_by_split: dict[str, list[dict[str, str]]]) -> dict[str, list[str]]:
    """Return glacier IDs after proving that no glacier crosses a split."""
    glaciers = {split: sorted({row["glacier_id"] for row in rows}) for split, rows in rows_by_split.items()}
    names = tuple(glaciers)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = set(glaciers[left]) & set(glaciers[right])
            if overlap:
                raise ValueError(f"glacier leakage between {left} and {right}: {sorted(overlap)}")
    return glaciers


def _load_dataset(dataset: Path) -> dict[str, Any]:
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("split_strategy") != "glacier_group_spatial_holdout":
        raise ValueError("dataset is not a glacier_group_spatial_holdout")
    if manifest.get("annotation_status") != "provisional_not_gold":
        raise ValueError("unexpected annotation status")

    payload: dict[str, Any] = {"manifest": manifest, "manifest_path": manifest_path}
    rows_by_split: dict[str, list[dict[str, str]]] = {}
    for split in ("train", "val", "test"):
        features = np.load(dataset / f"X_{split}.npy", mmap_mode="r")
        labels = np.load(dataset / f"y_{split}.npy", mmap_mode="r")
        weights = np.load(dataset / f"w_{split}.npy", mmap_mode="r")
        if features.shape[:3] != labels.shape or labels.shape != weights.shape:
            raise ValueError(f"{split} feature/label/weight shapes are inconsistent")
        if not np.isfinite(features).all() or not np.isfinite(weights).all():
            raise ValueError(f"{split} contains NaN or infinity")
        rows = _metadata(dataset / f"metadata_{split}.csv", split, len(features))
        payload[f"x_{split}"] = features
        payload[f"y_{split}"] = labels
        payload[f"w_{split}"] = weights
        rows_by_split[split] = rows
    payload["metadata"] = rows_by_split
    payload["glaciers"] = validate_glacier_disjoint(rows_by_split)
    return payload


def _aligned_probabilities(model, features: np.ndarray, *, batch_size: int) -> np.ndarray:
    probabilities = np.asarray(model.predict(features, batch_size=batch_size, verbose=0))
    if probabilities.shape[-1:] == (1,):
        probabilities = probabilities[..., 0]
    if probabilities.shape != features.shape[:3]:
        raise ValueError(f"unexpected probability shape {probabilities.shape}")
    if not np.isfinite(probabilities).all():
        raise ValueError("model probabilities contain NaN or infinity")
    return probabilities


def _reliable_values(
    labels: np.ndarray,
    probabilities: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    selected = np.asarray(weights) > 0
    if not selected.any():
        raise ValueError("no reliable pixels are available")
    return np.asarray(labels)[selected], np.asarray(probabilities)[selected]


def _evaluate(
    model,
    *,
    data: dict[str, Any],
    batch_size: int,
    pixel_area_m2: float,
    seed: int,
) -> dict[str, Any]:
    validation_probabilities = _aligned_probabilities(model, data["x_val"], batch_size=batch_size)
    validation_labels, validation_values = _reliable_values(
        data["y_val"],
        validation_probabilities,
        data["w_val"],
    )
    calibration = calibrate_threshold(
        validation_labels,
        validation_values,
        pixel_area_m2=pixel_area_m2,
    )
    threshold = float(calibration["selected_threshold"])

    test_probabilities = _aligned_probabilities(model, data["x_test"], batch_size=batch_size)
    test_labels, test_values = _reliable_values(data["y_test"], test_probabilities, data["w_test"])
    aggregate = {
        **hard_segmentation_metrics(test_labels, test_values, threshold),
        **area_metrics(test_labels, test_values, threshold, pixel_area_m2=pixel_area_m2),
    }

    per_glacier: list[dict[str, Any]] = []
    metadata = data["metadata"]["test"]
    for glacier_id in data["glaciers"]["test"]:
        indices = [index for index, row in enumerate(metadata) if row["glacier_id"] == glacier_id]
        labels = np.asarray(data["y_test"])[indices]
        probabilities = test_probabilities[indices]
        weights = np.asarray(data["w_test"])[indices]
        glacier_labels, glacier_values = _reliable_values(labels, probabilities, weights)
        per_glacier.append(
            {
                "glacier_id": glacier_id,
                "years": sorted({int(metadata[index]["year"]) for index in indices}),
                "patch_count": len(indices),
                **hard_segmentation_metrics(glacier_labels, glacier_values, threshold),
                **area_metrics(glacier_labels, glacier_values, threshold, pixel_area_m2=pixel_area_m2),
            }
        )

    return {
        "threshold_calibration": calibration,
        "test_metrics": aggregate,
        "probability_calibration": probability_calibration_metrics(test_labels, test_values),
        "per_glacier_metrics": per_glacier,
        "glacier_bootstrap": bootstrap_confidence_intervals(
            per_glacier,
            n_resamples=2000,
            seed=seed,
        ),
        "bootstrap_interpretation": (
            "Development diagnostic only: the spatial test contains two provisional-label glaciers, "
            "so intervals are retained for transparency but are not claim-grade."
        ),
    }


def _history_payload(history) -> dict[str, list[float]]:
    return {key: [float(value) for value in values] for key, values in history.history.items()}


def run(args: argparse.Namespace) -> dict[str, Any]:
    import tensorflow as tf

    started = time.perf_counter()
    tf.keras.utils.set_random_seed(args.seed)
    np.random.seed(args.seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        pass

    data = _load_dataset(args.dataset)
    model = tf.keras.models.load_model(
        args.initial_model,
        custom_objects=get_custom_objects(),
        compile=False,
    )
    expected_shape = tuple(int(value) for value in data["x_train"].shape[1:])
    if tuple(model.input_shape[1:]) != expected_shape:
        raise ValueError(f"initial model input {model.input_shape[1:]} != dataset {expected_shape}")

    baseline = _evaluate(
        model,
        data=data,
        batch_size=args.batch_size,
        pixel_area_m2=args.pixel_area_m2,
        seed=args.seed,
    )
    model = compile_model(model, learning_rate=args.learning_rate)
    generator = build_data_generator()
    train_generator = generator(
        data["x_train"],
        data["y_train"],
        batch_size=args.batch_size,
        augment=True,
        seed=args.seed,
        sample_weights=data["w_train"],
    )
    validation_generator = generator(
        data["x_val"],
        data["y_val"],
        batch_size=args.batch_size,
        augment=False,
        shuffle=False,
        sample_weights=data["w_val"],
    )

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.history_output.parent.mkdir(parents=True, exist_ok=True)
    callbacks = [
        tf.keras.callbacks.TerminateOnNaN(),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_dice_coefficient",
            mode="max",
            factor=0.5,
            patience=4,
            min_lr=1e-7,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_dice_coefficient",
            mode="max",
            patience=10,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(args.model_output),
            monitor="val_dice_coefficient",
            mode="max",
            save_best_only=True,
            save_format="tf",
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(str(args.history_output)),
    ]
    history = model.fit(
        train_generator,
        validation_data=validation_generator,
        epochs=args.epochs,
        callbacks=callbacks,
        verbose=2,
    )
    best_model = tf.keras.models.load_model(
        args.model_output,
        custom_objects=get_custom_objects(),
        compile=False,
    )
    candidate = _evaluate(
        best_model,
        data=data,
        batch_size=args.batch_size,
        pixel_area_m2=args.pixel_area_m2,
        seed=args.seed,
    )
    baseline_iou = float(baseline["test_metrics"]["hard_iou"])
    candidate_iou = float(candidate["test_metrics"]["hard_iou"])
    payload = {
        "schema": "glaciernet-kz.enhanced-spatial-evaluation.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "completed_provisional_not_gold",
        "claim_scope": "internal glacier-group spatial development test with provisional labels",
        "claims_allowed": [
            "the weighted training pipeline completed",
            "glacier IDs are disjoint across train, validation and test",
            "the reported internal test metrics were computed at a validation-selected threshold",
        ],
        "claims_not_allowed": [
            "independent expert accuracy",
            "external regional generalisation",
            "operational hazard performance",
        ],
        "git_commit": _git_commit(),
        "runtime": {
            "seconds": round(time.perf_counter() - started, 3),
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "platform": platform.platform(),
        },
        "dataset": {
            "path": str(args.dataset.relative_to(ROOT)),
            "manifest_sha256": _sha256(data["manifest_path"]),
            "annotation_status": data["manifest"]["annotation_status"],
            "split_strategy": data["manifest"]["split_strategy"],
            "glaciers": data["glaciers"],
            "patches": {split: int(len(data[f"x_{split}"])) for split in ("train", "val", "test")},
        },
        "training": {
            "initial_model": str(args.initial_model.relative_to(ROOT)),
            "initial_model_sha256": _sha256(args.initial_model),
            "output_model": str(args.model_output.relative_to(ROOT)),
            "output_model_sha256": sha256_directory(args.model_output),
            "epochs_requested": args.epochs,
            "epochs_completed": len(history.epoch),
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "seed": args.seed,
            "pixel_reliability_weights": True,
            "augmentation": True,
            "history": _history_payload(history),
        },
        "baseline_before_finetuning": baseline,
        "candidate_after_finetuning": candidate,
        "candidate_minus_baseline_test_hard_iou": candidate_iou - baseline_iou,
        "promotion": {
            "status": "improved_internal_spatial_test" if candidate_iou > baseline_iou else "not_promoted",
            "rule": "candidate test hard IoU must exceed the frozen initial model; this never upgrades the label tier",
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--initial-model", type=Path, default=DEFAULT_INITIAL_MODEL)
    parser.add_argument("--model-output", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--history-output", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--pixel-area-m2", type=float, default=100.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    for name in ("dataset", "initial_model", "model_output", "report", "history_output"):
        setattr(args, name, getattr(args, name).resolve())
    payload = run(args)
    summary = {
        "status": payload["status"],
        "epochs_completed": payload["training"]["epochs_completed"],
        "baseline_test": payload["baseline_before_finetuning"]["test_metrics"],
        "candidate_test": payload["candidate_after_finetuning"]["test_metrics"],
        "promotion": payload["promotion"],
        "report": str(args.report),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
