"""Read real on-disk pipeline coverage (raw data, predictions, tables)."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any


def _resolve_core_dir() -> Path:
    env_dir = os.environ.get("CORE_DIR")
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir))
    here = Path(__file__).resolve()
    candidates.extend([here.parents[3], here.parents[2], here.parents[2].parent])
    for candidate in candidates:
        if (candidate / "results").exists() and (candidate / "data").exists():
            return candidate
    return candidates[0]


CORE_DIR = _resolve_core_dir()
RESULTS_DIR = CORE_DIR / "results"
TABLES_DIR = RESULTS_DIR / "tables"
RAW_S2 = CORE_DIR / "data" / "raw" / "sentinel2"
RAW_LS = CORE_DIR / "data" / "raw" / "landsat"
PREDICTIONS_DIR = CORE_DIR / "predictions"


def _glob_years(directory: Path, prefix: str) -> list[int]:
    years: list[int] = []
    for path in directory.glob(f"{prefix}_*.tif"):
        try:
            years.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    return sorted(years)


def load_pipeline_status() -> dict[str, Any]:
    path = RESULTS_DIR / "pipeline_status.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_glacier_areas() -> list[dict[str, Any]]:
    path = TABLES_DIR / "glacier_areas_all_years.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_csv_table(name: str) -> list[dict[str, Any]]:
    path = TABLES_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_decision_readiness_summary() -> dict[str, Any]:
    path = RESULTS_DIR / "decision_readiness_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_data_coverage() -> dict[str, Any]:
    """Aggregate coverage from disk for dashboard and MCP tools."""
    status = load_pipeline_status()
    areas = load_glacier_areas()

    raw_s2 = _glob_years(RAW_S2, "sentinel2") if RAW_S2.exists() else []
    raw_ls = _glob_years(RAW_LS, "landsat") if RAW_LS.exists() else []
    predictions = (
        sorted(int(p.name) for p in PREDICTIONS_DIR.iterdir() if p.is_dir() and p.name.isdigit())
        if PREDICTIONS_DIR.exists()
        else []
    )

    target_s2 = status.get("sentinel2_years_target") or list(range(2015, 2025))
    target_ls = status.get("landsat_years_target") or [2000, 2003, 2005, 2008, 2010, 2013]

    rf_series = [
        {"year": int(row["year"]), "area_km2": float(row["area_km2"]), "sensor": row.get("sensor", "")}
        for row in areas
        if row.get("method", "").upper() == "RF"
    ]
    rf_series.sort(key=lambda x: x["year"])

    return {
        "raw_sentinel2": raw_s2,
        "raw_landsat": raw_ls,
        "predictions": predictions,
        "missing_sentinel2": [y for y in target_s2 if y not in raw_s2],
        "missing_landsat": [y for y in target_ls if y not in raw_ls],
        "missing_predictions": sorted(set(raw_s2 + raw_ls) - set(predictions)),
        "glacier_area_rf_series": rf_series,
        "areas_row_count": len(areas),
        "updated_from": "disk",
    }


def get_decision_readiness() -> dict[str, Any]:
    """Decision-facing data package: clean time series, year quality, trend summary."""
    return {
        "summary": load_decision_readiness_summary(),
        "timeseries": load_csv_table("decision_ready_area_timeseries.csv"),
        "year_quality": load_csv_table("year_quality_scores.csv"),
        "updated_from": str(RESULTS_DIR),
    }
