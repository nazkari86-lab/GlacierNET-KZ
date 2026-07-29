#!/usr/bin/env python3
"""Compare single-pass and flip-TTA inference without tuning on the test set."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_metrics import area_metrics, calibrate_threshold, hard_segmentation_metrics  # noqa: E402
from src.model_security import verify_trusted_model  # noqa: E402
from src.models import get_custom_objects, tta_predict_batch  # noqa: E402
from src.provenance import sha256_directory, sha256_file  # noqa: E402
from src.train import TrainConfig, load_data  # noqa: E402


def _materialize(values):
    return values[:] if hasattr(values, "__getitem__") else np.asarray(values)


def _evaluate(y_true, probability, threshold: float, pixel_area_m2: float) -> dict[str, float | int]:
    return {
        **hard_segmentation_metrics(y_true, probability, threshold),
        **area_metrics(y_true, probability, threshold, pixel_area_m2=pixel_area_m2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patches-dir",
        type=Path,
        default=ROOT / "data/processed/patches/sentinel2_terrain_s1_year_holdout_2017_2024",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=ROOT / "models/unet_best_sentinel2_terrain_s1_year_holdout_2017_2024",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--pixel-area-m2", type=float, default=100.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "benchmarks/v2/reports/inference_variants_s2_terrain_s1_2017_2024.json",
    )
    args = parser.parse_args()

    import tensorflow as tf

    patches = args.patches_dir.resolve()
    model_path = args.model.resolve()
    verify_trusted_model(model_path, root=ROOT)
    manifest_path = patches / "manifest.json"
    _, _, x_validation, y_validation, x_test, y_test = load_data(TrainConfig(patches_path=patches))
    x_validation = _materialize(x_validation)
    y_validation = _materialize(y_validation)
    x_test = _materialize(x_test)
    y_test = _materialize(y_test)
    model = tf.keras.models.load_model(model_path, custom_objects=get_custom_objects(), compile=False)

    variants: dict[str, dict[str, object]] = {}
    single_validation = model.predict(x_validation, batch_size=args.batch_size, verbose=0)[..., 0]
    single_test = model.predict(x_test, batch_size=args.batch_size, verbose=0)[..., 0]
    tta_validation, _ = tta_predict_batch(model, x_validation, batch_size=args.batch_size)
    tta_test, _ = tta_predict_batch(model, x_test, batch_size=args.batch_size)

    for name, validation_probability, test_probability in (
        ("single_pass", single_validation, single_test),
        ("flip_tta_4", tta_validation, tta_test),
    ):
        calibration = calibrate_threshold(
            y_validation,
            validation_probability,
            pixel_area_m2=args.pixel_area_m2,
        )
        threshold = float(calibration["selected_threshold"])
        variants[name] = {
            "threshold_calibration": calibration,
            "test_metrics": _evaluate(y_test, test_probability, threshold, args.pixel_area_m2),
        }

    selected = min(
        variants,
        key=lambda name: float(
            variants[name]["threshold_calibration"]["selected_metrics"]["calibration_objective"]  # type: ignore[index]
        ),
    )
    payload = {
        "schema": "glaciernet-kz.inference-variant-benchmark.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection_policy": "lowest pre-declared calibration objective on validation only",
        "test_policy": "test metrics were computed after variant and threshold selection",
        "selected_variant": selected,
        "deployment_default": "flip_tta_4" if selected == "flip_tta_4" else "single_pass",
        "model_path": str(model_path.relative_to(ROOT)),
        "model_sha256": sha256_directory(model_path),
        "patch_manifest": str(manifest_path.relative_to(ROOT)),
        "patch_manifest_sha256": sha256_file(manifest_path),
        "variants": variants,
        "claim_boundary": "One-AOI silver temporal holdout; not external-region or gold-label accuracy.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
