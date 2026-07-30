#!/usr/bin/env python3
"""Train and evaluate a reproducible real-data GLD lake baseline.

The validation split selects the probability threshold. The test split is
evaluated once with that frozen threshold. No test pixels enter training or
selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/external/centralasia_glacierbench/cryobench/GLD/GLNet"
ARCHIVE = ROOT / "data/external/centralasia_glacierbench/cryobench/GLD.tar.gz"
MODEL_PATH = ROOT / "models/centralasia_glacierbench_gld_hgb.joblib"
RESULT_PATH = ROOT / "benchmarks/centralasia_glacierbench/current/cryobench_gld_baseline.json"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _pairs(split: str) -> list[tuple[Path, Path]]:
    images = DATASET / split / "image"
    masks = DATASET / split / "mask"
    pairs = [(image, masks / image.name) for image in sorted(images.glob("*.tif"))]
    if not pairs or any(not mask.is_file() for _, mask in pairs):
        raise FileNotFoundError(f"incomplete GLD {split} split under {DATASET}")
    return pairs


def _read(pair: tuple[Path, Path]) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(pair[0]) as source:
        image = source.read().transpose(1, 2, 0).astype(np.float32)
    with rasterio.open(pair[1]) as source:
        mask = source.read(1).astype(bool)
    valid = np.isfinite(image).all(axis=2) & np.any(image != 0, axis=2)
    return image[valid], mask[valid]


def _training_pixels(
    pairs: list[tuple[Path, Path]],
    *,
    pixels_per_class_per_image: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    features: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    for pair in pairs:
        image, mask = _read(pair)
        for positive in (False, True):
            indices = np.flatnonzero(mask == positive)
            if indices.size == 0:
                continue
            count = min(pixels_per_class_per_image, indices.size)
            chosen = rng.choice(indices, size=count, replace=False)
            features.append(image[chosen])
            labels.append(mask[chosen].astype(np.uint8))
    return np.concatenate(features), np.concatenate(labels)


def _confusion(probability: np.ndarray, truth: np.ndarray, threshold: float) -> tuple[int, int, int, int]:
    prediction = probability >= threshold
    return (
        int(np.sum(prediction & truth)),
        int(np.sum(prediction & ~truth)),
        int(np.sum(~prediction & truth)),
        int(np.sum(~prediction & ~truth)),
    )


def _metrics(confusion: tuple[int, int, int, int]) -> dict[str, float | int]:
    tp, fp, fn, tn = confusion
    dice = 2 * tp / max(2 * tp + fp + fn, 1)
    iou = tp / max(tp + fp + fn, 1)
    return {
        "hard_dice_foreground": float(dice),
        "hard_iou_foreground": float(iou),
        "precision_foreground": float(tp / max(tp + fp, 1)),
        "recall_foreground": float(tp / max(tp + fn, 1)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _evaluate(
    model: HistGradientBoostingClassifier,
    pairs: list[tuple[Path, Path]],
    threshold: float,
) -> tuple[dict[str, float | int], list[dict[str, float | int | str]]]:
    total = np.zeros(4, dtype=np.int64)
    per_image: list[dict[str, float | int | str]] = []
    for pair in pairs:
        image, truth = _read(pair)
        probability = model.predict_proba(image)[:, 1]
        confusion = _confusion(probability, truth, threshold)
        total += np.asarray(confusion)
        per_image.append({"image_id": pair[0].stem, **_metrics(confusion)})
    return _metrics(tuple(int(value) for value in total)), per_image


def _bootstrap(
    rows: list[dict[str, float | int | str]],
    key: str,
    *,
    seed: int,
    resamples: int = 2000,
) -> dict[str, float | int]:
    values = np.asarray([float(row[key]) for row in rows])
    rng = np.random.default_rng(seed)
    sampled = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    return {
        "estimate": float(values.mean()),
        "ci_lower": float(np.quantile(sampled, 0.025)),
        "ci_upper": float(np.quantile(sampled, 0.975)),
        "confidence": 0.95,
        "n_images": int(len(values)),
        "n_resamples": resamples,
        "seed": seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pixels-per-class-per-image", type=int, default=512)
    parser.add_argument("--max-iter", type=int, default=120)
    parser.add_argument("--seed", type=int, default=142)
    args = parser.parse_args()
    train_pairs = _pairs("train")
    validation_pairs = _pairs("val")
    test_pairs = _pairs("test")
    x_train, y_train = _training_pixels(
        train_pairs,
        pixels_per_class_per_image=args.pixels_per_class_per_image,
        seed=args.seed,
    )
    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=args.max_iter,
        max_leaf_nodes=31,
        l2_regularization=0.1,
        random_state=args.seed,
    )
    model.fit(x_train, y_train)

    sweep: list[dict[str, float | int]] = []
    best_threshold = 0.5
    best_iou = -1.0
    for threshold in np.linspace(0.20, 0.80, 13):
        pooled, rows = _evaluate(model, validation_pairs, float(threshold))
        mean_iou = float(np.mean([row["hard_iou_foreground"] for row in rows]))
        sweep.append(
            {
                "threshold": float(threshold),
                "macro_image_hard_iou_foreground": mean_iou,
                "pooled_hard_iou_foreground": float(pooled["hard_iou_foreground"]),
            }
        )
        if mean_iou > best_iou:
            best_iou = mean_iou
            best_threshold = float(threshold)

    pooled_test, per_image_test = _evaluate(model, test_pairs, best_threshold)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    result = {
        "schema": "centralasia-glacierbench.cryobench-gld.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "measured_external_test",
        "task": "Cryo-Bench GLD glacial-lake foreground segmentation",
        "model": {
            "family": "HistGradientBoostingClassifier",
            "input_channels": 10,
            "training_pixels": int(len(y_train)),
            "class_balance_positive_fraction": float(y_train.mean()),
            "artifact": str(MODEL_PATH.relative_to(ROOT)),
            "artifact_sha256": _sha256(MODEL_PATH),
        },
        "protocol": {
            "train_images": len(train_pairs),
            "validation_images": len(validation_pairs),
            "test_images": len(test_pairs),
            "selection_split": "validation",
            "test_set_touched_for_selection": False,
            "selected_threshold": best_threshold,
            "primary_metric": "macro image-level foreground IoU",
            "metric_note": "Foreground IoU is reported explicitly; it is not assumed identical to publisher mIoU.",
            "seed": args.seed,
        },
        "validation_threshold_sweep": sweep,
        "test_pooled_metrics": pooled_test,
        "test_macro_bootstrap": {
            key: _bootstrap(per_image_test, key, seed=args.seed)
            for key in (
                "hard_dice_foreground",
                "hard_iou_foreground",
                "precision_foreground",
                "recall_foreground",
            )
        },
        "dataset": {
            "archive": str(ARCHIVE.relative_to(ROOT)),
            "archive_sha256": _sha256(ARCHIVE),
            "source": "Sk-21/Cryo-Bench GLD",
        },
        "claim_allowed": "reproducible lightweight baseline on the frozen real GLD test split",
        "claim_not_allowed": "operational lake detection in Kazakhstan without regional external validation",
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["test_macro_bootstrap"], indent=2))
    print(RESULT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
