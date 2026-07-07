"""WGMS validation data integrity tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WGMS_JSON = ROOT / "data" / "wgms" / "tuyuksu_areas.json"
WGMS_CSV = ROOT / "data" / "wgms" / "tuyuksu_areas.csv"
FOG_STATE = ROOT / "data" / "wgms" / "raw" / "fog_extracted" / "data" / "state.csv"


def test_tuyuksu_areas_json_exists_and_valid():
    assert WGMS_JSON.is_file(), f"Missing {WGMS_JSON}. Run: python scripts/download_wgms.py"
    data = json.loads(WGMS_JSON.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert len(data) >= 20, "Expected at least 20 years of Tuyuksu area observations"
    for year, area in data.items():
        assert int(year) >= 1950
        assert 0 < float(area) < 50, f"Unrealistic area {area} km² for year {year}"


def test_tuyuksu_areas_csv_exists():
    assert WGMS_CSV.is_file(), f"Missing {WGMS_CSV}. Run: python scripts/wgms_setup.py"


@pytest.mark.integration
def test_fog_state_csv_extracted():
    """Full FoG extract is optional in CI (large download); skip if absent."""
    if not FOG_STATE.is_file():
        pytest.skip("FoG state.csv not extracted — run python scripts/download_wgms.py")
    assert FOG_STATE.stat().st_size > 1_000_000
