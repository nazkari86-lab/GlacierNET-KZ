from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.local_data
def test_current_temporal_benchmark_has_claim_provenance():
    report = ROOT / "results" / "temporal_benchmark_unet_sentinel2_terrain_2016_2024.json"
    if not report.is_file():
        return
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_benchmark_report.py"), str(report)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_data_manifest_records_symlink_state():
    manifest = ROOT / "results" / "data_manifest.json"
    if not manifest.is_file():
        return
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["file_count"] + payload["symlink_count"] == len(payload["artifacts"])


def test_year_holdout_validator_passes_current_manifest():
    manifest = ROOT / "data/processed/patches/sentinel2_year_holdout_2016_2024/manifest.json"
    if not manifest.is_file():
        return
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_year_holdout.py"), str(manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_high_level_temporal_manifest_validation_alias():
    manifest = ROOT / "benchmarks/v2/manifests/temporal_holdout.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_year_holdout.py"), str(manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.local_data
def test_inference_variant_promotion_is_reproducible():
    report = ROOT / "benchmarks/v2/reports/inference_variants_s2_terrain_s1_2017_2024.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_inference_variant_benchmark.py"), str(report)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
