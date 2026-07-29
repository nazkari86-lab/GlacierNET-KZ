#!/usr/bin/env python3
"""Validate that a benchmark report contains enough provenance for claims."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = {
    "evaluation_protocol",
    "model_path",
    "patches_dir",
    "train_years",
    "validation_years",
    "test_years",
    "feature_schema",
    "metrics",
    "split_strategy",
    "label_provenance",
    "label_quality_tier",
    "generalisation_scope",
    "claims_allowed",
    "claims_not_allowed",
    "patch_manifest_sha256",
    "model_artifact_sha256",
}
ROOT = Path(__file__).resolve().parent.parent


def sha256_directory(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    for item in files:
        relative = item.relative_to(path).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    errors: list[str] = []
    errors.extend(f"missing top-level field: {key}" for key in sorted(REQUIRED - report.keys()))
    if not isinstance(report.get("test_years"), list) or not report.get("test_years"):
        errors.append("test_years must be non-empty")
    if set(report.get("train_years", [])) & set(report.get("test_years", [])):
        errors.append("train and test years overlap")
    if set(report.get("validation_years", [])) & set(report.get("test_years", [])):
        errors.append("validation and test years overlap")
    metrics = report.get("metrics", {})
    for key in ("dice_coefficient", "binary_io_u", "precision", "recall"):
        if key not in metrics:
            errors.append(f"missing metric: {key}")
        elif not 0.0 <= float(metrics[key]) <= 1.0:
            errors.append(f"metric outside [0,1]: {key}")
    protocol = str(report.get("evaluation_protocol", ""))
    if "untouched" not in protocol.lower() and "holdout" not in protocol.lower():
        errors.append("evaluation_protocol must state untouched holdout semantics")
    if report.get("split_strategy") != "year_holdout":
        errors.append("split_strategy must be year_holdout for this validator")
    if report.get("label_quality_tier") not in {"gold", "silver", "weak"}:
        errors.append("label_quality_tier must be gold, silver, or weak")
    if not report.get("claims_not_allowed"):
        errors.append("claims_not_allowed must be explicit")

    model_path = ROOT / str(report.get("model_path", ""))
    required_model_files = (
        model_path / "saved_model.pb",
        model_path / "variables" / "variables.index",
        model_path / "variables" / "variables.data-00000-of-00001",
    )
    for path in required_model_files:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty SavedModel artifact: {path.relative_to(ROOT)}")
        elif path.is_symlink():
            errors.append(f"SavedModel artifact must be local, not a symlink: {path.relative_to(ROOT)}")
    if all(path.is_file() and path.stat().st_size > 0 for path in required_model_files):
        actual_model_sha = sha256_directory(model_path)
        if report.get("model_artifact_sha256") != actual_model_sha:
            errors.append(f"model_artifact_sha256 does not match the current SavedModel ({actual_model_sha})")

    patches_dir = ROOT / str(report.get("patches_dir", ""))
    manifest_path = patches_dir / "manifest.json"
    if not manifest_path.is_file():
        errors.append(f"missing patch manifest: {manifest_path.relative_to(ROOT)}")
    else:
        actual_manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if report.get("patch_manifest_sha256") != actual_manifest_sha:
            errors.append(f"patch_manifest_sha256 does not match the current holdout manifest ({actual_manifest_sha})")
    if errors:
        print("BENCHMARK REPORT VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Benchmark report validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
