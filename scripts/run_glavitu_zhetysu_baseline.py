#!/usr/bin/env python3
"""Run the official pretrained GlaViTU model on the frozen Zhetysu replay.

The RGI-derived comparison layer is provisional silver evidence. Results test
external-model interoperability and failure containment, not independent
expert accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/external/centralasia_glacierbench/glavitu/scalable_glacier_mapping-1.0"
WEIGHTS = {
    "global": ROOT / "data/external/centralasia_glacierbench/glavitu/weights/glavitu_global_weights.h5",
    "hma": ROOT / "data/external/centralasia_glacierbench/glavitu/weights/glavitu_finetuning_HMA_weights.h5",
}
SCENES = ROOT / "data/external/provisional_zhetysu_2024"
RGI = ROOT / "data/rgi/RGI2000-v7.0-G-13_central_asia.shp"
OUTPUTS = {
    "hma": ROOT / "benchmarks/centralasia_glacierbench/current/glavitu_zhetysu_baseline.json",
    "global": ROOT / "benchmarks/centralasia_glacierbench/current/glavitu_zhetysu_global_baseline.json",
}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _features(
    path: Path,
) -> tuple[dict[str, np.ndarray], tuple[int, int, int, int], object, object]:
    with path.open("rb"):
        pass
    with rasterio.open(path) as dataset:
        raw = dataset.read().astype(np.float32)
        transform = dataset.transform
        crs = dataset.crs
    if raw.shape[0] != 10:
        raise ValueError(f"{path.name}: expected 7 Sentinel-2 and 3 terrain bands")
    raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    with (SOURCE / "utils/dataset_stats.pickle").open("rb") as handle:
        mins, maxs = pickle.load(handle)
    optical = np.moveaxis(raw[[0, 1, 2, 3, 5, 6]], 0, -1) / 10_000.0
    optical = (optical - mins["optical"]) / (maxs["optical"] - mins["optical"])
    elevation = (raw[7] - mins["elevation"][0]) / (maxs["elevation"][0] - mins["elevation"][0])
    slope = (raw[8] - mins["slope"][0]) / (maxs["slope"][0] - mins["slope"][0])
    dem = np.stack([elevation, slope], axis=-1)
    height, width = optical.shape[:2]
    padded_height = max(384, height)
    padded_width = max(384, width)
    top = (padded_height - height) // 2
    left = (padded_width - width) // 2
    padded_optical = np.zeros((padded_height, padded_width, 6), dtype=np.float32)
    padded_dem = np.zeros((padded_height, padded_width, 2), dtype=np.float32)
    padded_optical[top : top + height, left : left + width] = np.nan_to_num(optical)
    padded_dem[top : top + height, left : left + width] = np.nan_to_num(dem)
    return (
        {"optical": padded_optical, "dem": padded_dem},
        (height, width, top, left),
        transform,
        crs,
    )


def _starts(size: int) -> list[int]:
    starts = list(range(0, max(size - 384 + 1, 1), 192))
    final = max(size - 384, 0)
    if final not in starts:
        starts.append(final)
    return starts


def _predict_tiled(model, features: dict[str, np.ndarray]) -> np.ndarray:
    height, width = features["optical"].shape[:2]
    patches: dict[str, list[np.ndarray]] = {"optical": [], "dem": []}
    locations: list[tuple[int, int]] = []
    for row in _starts(height):
        for col in _starts(width):
            for name in patches:
                patches[name].append(features[name][row : row + 384, col : col + 384])
            locations.append((row, col))
    batch = {name: np.asarray(values) for name, values in patches.items()}
    predictions = model.predict(batch, verbose=0)[..., 1]
    probability = np.zeros((height, width), dtype=np.float32)
    counts = np.zeros((height, width), dtype=np.uint8)
    for (row, col), prediction in zip(locations, predictions):
        probability[row : row + 384, col : col + 384] += prediction
        counts[row : row + 384, col : col + 384] += 1
    return probability / np.maximum(counts, 1)


def _metrics(truth: np.ndarray, prediction: np.ndarray) -> dict[str, float | int]:
    tp = int(np.sum(truth & prediction))
    fp = int(np.sum(~truth & prediction))
    fn = int(np.sum(truth & ~prediction))
    return {
        "hard_dice": float(2 * tp / max(2 * tp + fp + fn, 1)),
        "hard_iou": float(tp / max(tp + fp + fn, 1)),
        "precision": float(tp / max(tp + fp, 1)),
        "recall": float(tp / max(tp + fn, 1)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def _bootstrap(rows: list[dict[str, object]], key: str, seed: int) -> dict[str, float | int]:
    values = np.asarray([float(row[key]) for row in rows])
    rng = np.random.default_rng(seed)
    estimates = rng.choice(values, size=(2000, len(values)), replace=True).mean(axis=1)
    return {
        "estimate": float(values.mean()),
        "ci_lower": float(np.quantile(estimates, 0.025)),
        "ci_upper": float(np.quantile(estimates, 0.975)),
        "confidence": 0.95,
        "n_glaciers": len(values),
        "n_resamples": 2000,
        "seed": seed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=sorted(WEIGHTS), default="hma")
    parser.add_argument("--seed", type=int, default=142)
    parser.add_argument("--max-scenes", type=int)
    args = parser.parse_args()
    weight_path = WEIGHTS[args.strategy]
    if not weight_path.is_file():
        raise FileNotFoundError(weight_path)
    sys.path.insert(0, str(SOURCE))
    from models.mapping.glavitu import GlaViTU

    train_model, test_model = GlaViTU(
        {"optical": (384, 384, 6), "dem": (384, 384, 2)},
        n_outputs=2,
        use_deepsupervision=True,
        dropout=0.10,
        inference_dropout=False,
    )
    train_model.load_weights(weight_path)
    rgi = gpd.read_file(RGI).set_index("rgi_id")
    rows: list[dict[str, object]] = []
    scenes = sorted(SCENES.glob("*_2024.tif"))
    if args.max_scenes is not None:
        scenes = scenes[: args.max_scenes]
    for scene in scenes:
        glacier_id = scene.stem.removesuffix("_2024")
        if glacier_id not in rgi.index:
            continue
        features, (height, width, top, left), transform, crs = _features(scene)
        probability = _predict_tiled(test_model, features)
        prediction = probability[top : top + height, left : left + width] >= 0.5
        geometry = gpd.GeoSeries([rgi.loc[glacier_id].geometry], crs=rgi.crs).to_crs(crs).iloc[0]
        truth = rasterize(
            [(geometry, 1)],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8,
        ).astype(bool)
        rows.append(
            {
                "rgi_id": glacier_id,
                "scene_sha256": _sha256(scene),
                **_metrics(truth, prediction),
                "predicted_fraction": float(prediction.mean()),
            }
        )
        print(glacier_id, rows[-1]["hard_iou"], flush=True)
    if not rows:
        raise RuntimeError("No frozen Zhetysu replay scenes were evaluated")
    result = {
        "schema": "centralasia-glacierbench.glavitu-zhetysu.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "measured_provisional_external_model",
        "model": "GlaViTU",
        "strategy": args.strategy,
        "weights_sha256": _sha256(weight_path),
        "threshold": 0.5,
        "threshold_source": "fixed softmax argmax; no Zhetysu tuning",
        "feature_schema": ["B2", "B3", "B4", "B8", "B11", "B12", "elevation", "slope"],
        "metrics_bootstrap": {
            key: _bootstrap(rows, key, args.seed) for key in ("hard_dice", "hard_iou", "precision", "recall")
        },
        "per_glacier": rows,
        "label_quality_tier": "provisional_silver_rgi",
        "claim_allowed": "official external pretrained-model interoperability on the frozen replay",
        "claim_not_allowed": "independent external accuracy or current-boundary truth",
        "circularity_guard": (
            "The 2024 prediction is compared with an RGI-derived inventory layer. "
            "The metric measures inventory consistency, not expert-verified 2024 accuracy."
        ),
    }
    output = OUTPUTS[args.strategy]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
