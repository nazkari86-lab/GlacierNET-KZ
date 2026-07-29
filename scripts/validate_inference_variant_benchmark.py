#!/usr/bin/env python3
"""Fail closed if the inference-variant promotion artifact is inconsistent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.provenance import sha256_directory, sha256_file  # noqa: E402


def validate(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("schema") != "glaciernet-kz.inference-variant-benchmark.v1":
        errors.append("invalid schema")
    variants = payload.get("variants")
    if not isinstance(variants, dict) or set(variants) != {"single_pass", "flip_tta_4"}:
        return errors + ["single_pass and flip_tta_4 variants are required"]
    try:
        objectives = {
            name: float(value["threshold_calibration"]["selected_metrics"]["calibration_objective"])
            for name, value in variants.items()
        }
        selected = min(objectives, key=objectives.get)
    except (KeyError, TypeError, ValueError):
        return errors + ["invalid validation calibration records"]
    if payload.get("selected_variant") != selected:
        errors.append("selected_variant is not the validation-objective winner")
    if payload.get("deployment_default") != selected:
        errors.append("deployment_default does not match selected_variant")
    for name, value in variants.items():
        metrics = value.get("test_metrics", {})
        for metric in ("hard_dice", "hard_iou", "precision", "recall", "area_error_percent"):
            try:
                number = float(metrics[metric])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{name}: invalid {metric}")
                continue
            if metric != "area_error_percent" and not 0 <= number <= 1:
                errors.append(f"{name}: {metric} outside [0, 1]")
    model = ROOT / str(payload.get("model_path", ""))
    manifest = ROOT / str(payload.get("patch_manifest", ""))
    if not model.exists() or sha256_directory(model) != payload.get("model_sha256"):
        errors.append("model SHA-256 mismatch")
    if not manifest.is_file() or sha256_file(manifest) != payload.get("patch_manifest_sha256"):
        errors.append("patch manifest SHA-256 mismatch")
    if "validation only" not in str(payload.get("selection_policy", "")):
        errors.append("selection policy must be validation-only")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=ROOT / "benchmarks/v2/reports/inference_variants_s2_terrain_s1_2017_2024.json",
    )
    args = parser.parse_args()
    errors = validate(args.report)
    if errors:
        print("INFERENCE VARIANT BENCHMARK VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Inference variant benchmark validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
