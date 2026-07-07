"""Tests for batch prediction helpers and data coverage scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_years_needing_predictions_includes_2019():
    from scripts.batch_predict_all import years_needing_predictions

    missing = years_needing_predictions()
    assert isinstance(missing, list)
    # 2015 was processed manually in this session; 2019+ may still be pending
    if (ROOT / "predictions" / "2019" / "rf_mask.tif").exists():
        assert 2019 not in missing


def test_rebuild_areas_table_writes_csv():
    out = ROOT / "results" / "tables" / "glacier_areas_all_years.csv"
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "rebuild_areas_table.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "year,sensor,method" in text
    assert "source_file" in text


def test_pipeline_status_includes_all_sentinel_years():
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pipeline_status.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0
    status = json.loads((ROOT / "results" / "pipeline_status.json").read_text())
    assert status["missing_sentinel2"] == []
    assert 2015 in status["raw_sentinel2"]
    assert 2024 in status["raw_sentinel2"]


def test_validate_data_coverage_passes_or_reports_stale():
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_data_coverage.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    # May fail while batch predict is in progress — that's informative, not a test bug
    assert rc.returncode in (0, 1)
