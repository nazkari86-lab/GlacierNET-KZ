#!/usr/bin/env python3
"""Evaluate a saved model on the untouched test years of a holdout manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_metrics import area_metrics, calibrate_threshold, hard_segmentation_metrics  # noqa: E402
from src.model_security import verify_trusted_model  # noqa: E402
from src.models import build_data_generator, compile_model, get_custom_objects  # noqa: E402
from src.provenance import sha256_directory  # noqa: E402
from src.train import TrainConfig, load_data  # noqa: E402


def report_payload(
    model_path: Path,
    patches_dir: Path,
    metrics: dict[str, float],
    test_shape: tuple[int, ...],
    *,
    benchmark_v2: dict | None = None,
) -> dict:
    manifest = json.loads((patches_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest_bytes = (patches_dir / "manifest.json").read_bytes()
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "benchmark_protocol_version": "1.0" if benchmark_v2 is None else "2.0",
        "evaluation_protocol": "untouched temporal test-year holdout",
        "split_strategy": "year_holdout",
        "label_provenance": "RGI-derived masks; not independent expert gold labels",
        "label_quality_tier": "silver",
        "generalisation_scope": "one AOI temporal validation only",
        "claims_allowed": ["temporal holdout benchmark", "research baseline comparison"],
        "claims_not_allowed": ["cross-region generalisation", "field accuracy", "operational readiness"],
        "patch_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "model_artifact_sha256": sha256_directory(model_path),
        "model_path": str(model_path.relative_to(ROOT)),
        "patches_dir": str(patches_dir.relative_to(ROOT)),
        "train_years": manifest.get("train_years", []),
        "validation_years": manifest.get("val_years", []),
        "test_years": manifest.get("test_years", []),
        "feature_schema": manifest.get("feature_schema", []),
        "test_patch_shape": list(test_shape),
        "metric_semantics": {
            "metrics": "framework metrics retained for backward compatibility; dice_coefficient is soft",
            "hard_metrics": "all overlap metrics use one validation-calibrated binary threshold",
        },
        "metrics": {name: float(value) for name, value in metrics.items()},
    }
    if benchmark_v2 is not None:
        payload.update(benchmark_v2)
    return payload


def _aligned_mask(label: object, prediction: object):
    import numpy as np

    label_array = np.asarray(label)
    prediction_array = np.asarray(prediction)
    if label_array.shape == prediction_array.shape:
        return label_array, prediction_array
    if prediction_array.shape[-1:] == (1,) and prediction_array.shape[:-1] == label_array.shape:
        return label_array, prediction_array[..., 0]
    if label_array.shape[-1:] == (1,) and label_array.shape[:-1] == prediction_array.shape:
        return label_array[..., 0], prediction_array
    raise ValueError(f"label/prediction shape mismatch: {label_array.shape} vs {prediction_array.shape}")


def benchmark_v2_metrics(
    model,
    x_validation,
    y_validation,
    x_test,
    y_test,
    *,
    batch_size: int,
    pixel_area_m2: float,
) -> dict:
    """Calibrate on validation probabilities, then freeze the test threshold."""
    validation_probabilities = model.predict(x_validation, batch_size=batch_size, verbose=0)
    validation_labels, validation_probabilities = _aligned_mask(y_validation, validation_probabilities)
    calibration = calibrate_threshold(
        validation_labels,
        validation_probabilities,
        pixel_area_m2=pixel_area_m2,
    )
    threshold = float(calibration["selected_threshold"])
    test_probabilities = model.predict(x_test, batch_size=batch_size, verbose=0)
    test_labels, test_probabilities = _aligned_mask(y_test, test_probabilities)
    hard = {
        **hard_segmentation_metrics(test_labels, test_probabilities, threshold),
        **area_metrics(test_labels, test_probabilities, threshold, pixel_area_m2=pixel_area_m2),
    }
    return {
        "threshold_calibration": calibration,
        "hard_metrics": hard,
        "boundary_metrics_status": "blocked: glacier-aware non-overlapping test geometry is required",
        "bootstrap_status": "blocked: glacier_id is absent from the current silver patch manifest",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patches-dir",
        type=Path,
        default=ROOT / "data/processed/patches/sentinel2_terrain_year_holdout_2016_2024",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "models/unet_best_sentinel2_terrain_year_holdout_2016_2024",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--pixel-area-m2", type=float, default=100.0)
    parser.add_argument("--focal", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json",
    )
    args = parser.parse_args()
    patches_dir = args.patches_dir.resolve()
    model_path = args.model.resolve()

    import tensorflow as tf

    _, _, x_validation, y_validation, x_test, y_test = load_data(TrainConfig(patches_path=patches_dir))
    verify_trusted_model(model_path, root=ROOT)
    model = tf.keras.models.load_model(model_path, custom_objects=get_custom_objects(), compile=False)
    compile_model(model, use_focal=args.focal)
    generator = build_data_generator()(x_test, y_test, batch_size=args.batch_size, augment=False, shuffle=False)
    metrics = model.evaluate(generator, verbose=1, return_dict=True)
    v2 = benchmark_v2_metrics(
        model,
        x_validation,
        y_validation,
        x_test,
        y_test,
        batch_size=args.batch_size,
        pixel_area_m2=args.pixel_area_m2,
    )
    payload = report_payload(
        model_path,
        patches_dir,
        metrics,
        tuple(int(value) for value in x_test.shape),
        benchmark_v2=v2,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
