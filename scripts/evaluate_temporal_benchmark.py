#!/usr/bin/env python3
"""Evaluate a saved model on the untouched test years of a holdout manifest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import build_data_generator, compile_model, get_custom_objects  # noqa: E402
from src.train import TrainConfig, load_data  # noqa: E402


def report_payload(model_path: Path, patches_dir: Path, metrics: dict[str, float], test_shape: tuple[int, ...]) -> dict:
    manifest = json.loads((patches_dir / "manifest.json").read_text(encoding="utf-8"))
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluation_protocol": "untouched temporal test-year holdout",
        "model_path": str(model_path.relative_to(ROOT)),
        "patches_dir": str(patches_dir.relative_to(ROOT)),
        "train_years": manifest.get("train_years", []),
        "validation_years": manifest.get("val_years", []),
        "test_years": manifest.get("test_years", []),
        "feature_schema": manifest.get("feature_schema", []),
        "test_patch_shape": list(test_shape),
        "metrics": {name: float(value) for name, value in metrics.items()},
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

    _, _, _, _, x_test, y_test = load_data(TrainConfig(patches_path=patches_dir))
    model = tf.keras.models.load_model(model_path, custom_objects=get_custom_objects(), compile=False)
    compile_model(model, use_focal=args.focal)
    generator = build_data_generator()(x_test, y_test, batch_size=args.batch_size, augment=False, shuffle=False)
    metrics = model.evaluate(generator, verbose=1, return_dict=True)
    payload = report_payload(model_path, patches_dir, metrics, tuple(int(value) for value in x_test.shape))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
