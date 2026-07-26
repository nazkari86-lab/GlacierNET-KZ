#!/usr/bin/env python3
"""Run the reproducibility and scientific quality gates in one command."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(label: str, command: list[str]) -> bool:
    print(f"\n[quality-gate] {label}")
    normalized = list(command)
    if normalized and normalized[0] in {"python", "python3"}:
        normalized[0] = sys.executable
    result = subprocess.run(normalized, cwd=ROOT)
    print(f"[quality-gate] {label}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-symlinks", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    python = sys.executable
    checks: list[tuple[str, list[str]]] = [
        ("compile", [python, "-m", "compileall", "-q", "src", "scripts"]),
        ("data manifest", [python, "scripts/build_data_manifest.py"]),
        (
            "data integrity",
            [python, "scripts/validate_data_manifest.py"] + (["--allow-symlinks"] if args.allow_symlinks else []),
        ),
        ("training masks", [python, "scripts/validate_training_masks.py", "--years", "2016-2024"]),
        ("ancillary alignment", [python, "scripts/validate_ancillary_features.py"]),
        ("decision readiness", [python, "scripts/validate_decision_readiness.py"]),
        ("benchmark v2 published tables", [python, "scripts/build_benchmark_v2_tables.py"]),
        ("benchmark v2 structure", [python, "scripts/validate_benchmark_v2.py", "--allow-incomplete"]),
        ("provisional glacier cohorts", [python, "scripts/validate_provisional_cohorts.py"]),
        ("scientific claims registry", [python, "scripts/validate_claims_registry.py"]),
        ("cascade event review queue", [python, "scripts/build_cascade_review_queue.py"]),
        (
            "cascade benchmark structure",
            [python, "scripts/validate_cascade_benchmark.py", "--allow-incomplete"],
        ),
        ("trusted model artifacts", [python, "scripts/validate_trusted_models.py"]),
        ("model release manifest", [python, "scripts/build_model_release_manifest.py"]),
        ("local release package", [python, "scripts/verify_local_release_package.py"]),
    ]
    patch_manifests = [
        (
            "baseline patch arrays",
            ROOT / "data/processed/patches/sentinel2_multiyear_sample_2016_2024/manifest.json",
            "2016-2024",
        ),
        (
            "terrain patch arrays",
            ROOT / "data/processed/patches/sentinel2_terrain_sample_2016_2024/manifest.json",
            "2016-2024",
        ),
        (
            "controlled 14-channel ablation arrays",
            ROOT / "data/processed/patches/sentinel2_terrain_control_ablation_2017_2024/manifest.json",
            "2017-2024",
        ),
        (
            "controlled Sentinel-1 ablation arrays",
            ROOT / "data/processed/patches/sentinel2_terrain_s1_ablation_2017_2024/manifest.json",
            "2017-2024",
        ),
    ]
    for label, manifest, required_years in patch_manifests:
        if manifest.is_file():
            checks.append(
                (
                    label,
                    [
                        python,
                        "scripts/validate_patch_manifest.py",
                        str(manifest),
                        "--require-years",
                        required_years,
                    ],
                )
            )
    benchmark = ROOT / "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json"
    if benchmark.is_file():
        checks.append(("benchmark provenance", [python, "scripts/validate_benchmark_report.py", str(benchmark)]))
    holdouts = [
        (
            "baseline year holdout leakage",
            ROOT / "data/processed/patches/sentinel2_year_holdout_2016_2024/manifest.json",
        ),
        (
            "terrain year holdout leakage",
            ROOT / "data/processed/patches/sentinel2_terrain_year_holdout_2016_2024/manifest.json",
        ),
        (
            "controlled 14-channel holdout leakage",
            ROOT / "data/processed/patches/sentinel2_terrain_control_year_holdout_2017_2024/manifest.json",
        ),
        (
            "controlled Sentinel-1 holdout leakage",
            ROOT / "data/processed/patches/sentinel2_terrain_s1_year_holdout_2017_2024/manifest.json",
        ),
    ]
    for label, holdout in holdouts:
        if holdout.is_file():
            checks.append((label, [python, "scripts/validate_year_holdout.py", str(holdout)]))
    ablation = ROOT / "results/ablation_sentinel1_2017_2024.json"
    if ablation.is_file():
        checks.append(
            ("controlled Sentinel-1 ablation evidence", [python, "scripts/validate_ablation_report.py", str(ablation)])
        )
    checks.append(("prediction coverage and georeferencing", [python, "scripts/validate_predictions.py"]))
    if not args.skip_tests:
        checks.append(("unit and integration tests", [python, "-m", "pytest", "-q", "--no-cov"]))
    passed = all(run(label, command) for label, command in checks)
    print(f"\nQuality gates: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
