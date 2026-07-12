"""Tests for decision-ready provenance tables and validation script."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_build_decision_readiness_tables_adds_provenance_columns():
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_decision_readiness_tables.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr

    table = ROOT / "results" / "tables" / "decision_ready_area_timeseries.csv"
    with table.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert rows
    assert "model_file" in rows[0]
    assert "git_or_snapshot_id" in rows[0]
    row_2015 = next(row for row in rows if row["year"] == "2015")
    assert row_2015["source_flag"] == "sentinel2_toa_fallback"
    assert row_2015["include_in_strict_trend"] == "False"
    assert all(row["source_flag"] != "sentinel2_sr_or_harmonized" for row in rows)


def test_validate_decision_readiness_passes():
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_decision_readiness.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "Decision readiness validation passed" in rc.stdout
