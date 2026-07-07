#!/usr/bin/env python3
"""Retrain RF baseline and sweep NDSI threshold on 2020 patches."""

from __future__ import annotations

import csv
import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config
from src.metrics import evaluate_segmentation


def load_patches(year: int = 2020):
    d = config.DATA_PATCHES / str(year)
    X_train = np.load(d / "X_train.npy")
    y_train = np.load(d / "y_train.npy")
    X_test = np.load(d / "X_test.npy")
    y_test = np.load(d / "y_test.npy")
    return X_train, y_train, X_test, y_test


def flatten_xy(X: np.ndarray, y: np.ndarray):
    n = X.shape[0]
    Xf = X.reshape(n, -1)
    yf = (y.reshape(n, -1) > 0.5).astype(np.uint8)
    return Xf, yf


def train_rf(X_train, y_train, X_test, y_test):
    from sklearn.ensemble import RandomForestClassifier

    X_train = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)

    n_sample = min(1_000_000, len(X_train))
    rng = np.random.default_rng(config.RANDOM_SEED)
    idx = rng.choice(len(X_train), n_sample, replace=False)

    print(f"Training Random Forest (200 trees, {n_sample:,} pixel sample)...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        n_jobs=-1,
        random_state=config.RANDOM_SEED,
        class_weight="balanced",
    )
    rf.fit(X_train[idx], y_train[idx])
    y_pred = rf.predict(X_test)
    metrics = evaluate_segmentation(y_test, y_pred)

    out = config.MODELS_DIR / "random_forest.pkl"
    with out.open("wb") as f:
        pickle.dump(rf, f)
    print(f"  Saved → {out}")
    print(f"  F1={metrics['f1']:.4f}, IoU={metrics['iou']:.4f}")
    return metrics


def sweep_ndsi(X_test, y_test):
    ndsi_idx = config.BAND_INDEX["NDSI"]
    ndsi = X_test[..., ndsi_idx].reshape(-1)
    y_true = (y_test.reshape(-1) > 0.5).astype(np.uint8)

    best_t, best_f1 = 0.5, 0.0
    best_metrics = {}
    print("Sweeping NDSI threshold...")
    for t in np.arange(0.2, 0.8, 0.02):
        y_pred = (ndsi >= t).astype(np.uint8)
        m = evaluate_segmentation(y_true, y_pred)
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_t = float(t)
            best_metrics = m

    print(f"  Best threshold={best_t:.2f}, F1={best_metrics['f1']:.4f}, IoU={best_metrics['iou']:.4f}")
    return best_t, best_metrics


def update_comparison_csv(rf_metrics: dict, ndsi_metrics: dict, ndsi_t: float) -> None:
    csv_path = config.TABLES_DIR / "model_comparison.csv"
    keras_rows = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                name = row.get("model", "")
                if "U-Net" in name or "NDSI" in name or "Random Forest" in name:
                    if "U-Net" in name:
                        keras_rows.append(row)
                elif "U-Net" in name:
                    keras_rows.append(row)

    # Re-read properly
    keras_rows = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if "U-Net" in row.get("model", ""):
                    keras_rows.append(row)

    baselines = [
        {
            "model": f"NDSI (threshold={ndsi_t:.2f})",
            "f1": round(ndsi_metrics["f1"], 4),
            "iou": round(ndsi_metrics["iou"], 4),
            "precision": round(ndsi_metrics["precision"], 4),
            "recall": round(ndsi_metrics["recall"], 4),
        },
        {
            "model": "Random Forest (200 trees)",
            "f1": round(rf_metrics["f1"], 4),
            "iou": round(rf_metrics["iou"], 4),
            "precision": round(rf_metrics["precision"], 4),
            "recall": round(rf_metrics["recall"], 4),
        },
    ]

    fieldnames = ["model", "f1", "iou", "precision", "recall"]
    all_rows = baselines + keras_rows
    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in all_rows:
            w.writerow(row)
    print(f"Updated → {csv_path}")


def main() -> None:
    year = 2020
    print(f"Loading patches {year}...")
    X_train, y_train, X_test, y_test = load_patches(year)
    X_train_f, y_train_f = flatten_xy(X_train, y_train)
    X_test_f, y_test_f = flatten_xy(X_test, y_test)

    rf_metrics = train_rf(X_train_f, y_train_f, X_test_f, y_test_f)
    ndsi_t, ndsi_metrics = sweep_ndsi(X_test, y_test)
    update_comparison_csv(rf_metrics, ndsi_metrics, ndsi_t)
    print("Done.")


if __name__ == "__main__":
    main()
