"""Tests for yearly training mask validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_existing_2021_training_mask_is_valid_without_manifest():
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_training_masks.py"),
            "--years",
            "2021",
            "--skip-manifest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "Training mask validation passed" in rc.stdout


def test_training_mask_validation_rejects_2015_without_explicit_flag():
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_training_masks.py"),
            "--years",
            "2015",
            "--skip-manifest",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 1
    assert "2015 fallback" in rc.stdout
