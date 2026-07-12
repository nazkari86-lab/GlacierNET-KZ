"""Tests for multi-year Sentinel-2 patch manifest validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_existing_multiyear_sample_manifest_is_valid():
    manifest = ROOT / "data" / "processed" / "patches" / "sentinel2_multiyear_sample" / "manifest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_patch_manifest.py"),
            str(manifest),
            "--require-years",
            "2021",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "Patch manifest validation passed" in rc.stdout


def test_existing_2016_2024_capped_sample_manifest_is_valid():
    manifest = ROOT / "data" / "processed" / "patches" / "sentinel2_multiyear_sample_2016_2024" / "manifest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_patch_manifest.py"),
            str(manifest),
            "--require-years",
            "2016-2024",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "Patch manifest validation passed" in rc.stdout


def test_year_holdout_manifest_is_valid():
    manifest = ROOT / "data" / "processed" / "patches" / "sentinel2_year_holdout_2016_2024" / "manifest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_patch_manifest.py"),
            str(manifest),
            "--require-years",
            "2016-2024",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "Patch manifest validation passed" in rc.stdout


def test_patch_manifest_rejects_wrong_required_years():
    manifest = ROOT / "data" / "processed" / "patches" / "sentinel2_multiyear_sample" / "manifest.json"
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_patch_manifest.py"),
            str(manifest),
            "--require-years",
            "2016-2024",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 1
    assert "required years" in rc.stdout
