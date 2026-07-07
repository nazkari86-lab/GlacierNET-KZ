#!/usr/bin/env python3
"""Evaluate all trained models on the 2020 test patch set and update model_comparison.csv."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.metrics import evaluate_segmentation
from src.models import build_data_generator, build_model_by_name, get_custom_objects


MODELS = [
    ("unet", "U-Net (Baseline)"),
    ("attention_unet", "U-Net (Attention)"),
    ("unet_plus_plus", "U-Net++"),
]


def load_test_data(year: int = 2020):
    patches_dir = config.DATA_PATCHES / str(year)
    X_test = np.load(patches_dir / "X_test.npy")
    y_test = np.load(patches_dir / "y_test.npy")
    return X_test, y_test


def evaluate_keras_model(model_name: str, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    import tensorflow as tf

    weights = config.MODELS_DIR / f"{model_name}_best.h5"
    if not weights.exists():
        raise FileNotFoundError(f"Missing weights: {weights}")

    input_shape = (config.PATCH_SIZE, config.PATCH_SIZE, config.N_CHANNELS)
    model = build_model_by_name(model_name, input_shape)
    model.load_weights(str(weights))

    GlacierDataGenerator = build_data_generator()
    # predict on full array to avoid generator sample-count mismatch
    y_pred_probs = model.predict(X_test, batch_size=config.BATCH_SIZE, verbose=0)
    if y_pred_probs.ndim == 4 and y_pred_probs.shape[-1] == 1:
        y_pred_probs = y_pred_probs[..., 0]
    y_pred = (y_pred_probs >= 0.5).astype(np.uint8)
    return evaluate_segmentation(y_test, y_pred)


def main() -> None:
    year = 2020
    print(f"Loading test patches for {year}...")
    X_test, y_test = load_test_data(year)
    print(f"Test set: {X_test.shape[0]} patches")

    rows: list[dict] = []
    for model_name, display_name in MODELS:
        print(f"\nEvaluating {display_name} ({model_name})...")
        try:
            metrics = evaluate_keras_model(model_name, X_test, y_test)
            row = {
                "model": display_name,
                "f1": round(metrics["f1"], 4),
                "iou": round(metrics["iou"], 4),
                "precision": round(metrics["precision"], 4),
                "recall": round(metrics["recall"], 4),
            }
            rows.append(row)
            print(f"  F1={row['f1']}, IoU={row['iou']}")
        except FileNotFoundError as exc:
            print(f"  SKIP: {exc}")

    # Preserve baseline rows (NDSI, RF) from existing CSV if present
    csv_path = config.TABLES_DIR / "model_comparison.csv"
    baselines = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("model", "")
                if "NDSI" in name or "Random Forest" in name:
                    baselines.append(row)

    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["model", "f1", "iou", "precision", "recall"]
    all_rows = baselines + rows

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row[k] for k in fieldnames})

    print(f"\nUpdated → {csv_path}")
    for row in all_rows:
        print(f"  {row['model']}: F1={row['f1']}, IoU={row['iou']}")


if __name__ == "__main__":
    main()
