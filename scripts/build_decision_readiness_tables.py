#!/usr/bin/env python3
"""Build decision-ready time series and year quality tables.

The raw research tables keep every available prediction. Public reports and
pilot materials need a stricter view: explicit data-source flags, caveats, and
a clean trend subset that does not silently mix fallback imagery with standard
summer composites.
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, metrics  # noqa: E402

AREAS_CSV = config.TABLES_DIR / "glacier_areas_all_years.csv"
QUALITY_CSV = config.TABLES_DIR / "year_quality_scores.csv"
DECISION_TS_CSV = config.TABLES_DIR / "decision_ready_area_timeseries.csv"
DECISION_SUMMARY_JSON = config.RESULTS_DIR / "decision_readiness_summary.json"

METHOD_PRIORITY = ["RF", "U-Net", "NDSI"]
MODEL_FILES = {
    "RF": "models/random_forest.pkl",
    "U-Net": "models/unet_best.h5",
    "NDSI": "spectral_index:ndsi",
}


def read_area_rows() -> list[dict[str, str]]:
    if not AREAS_CSV.exists():
        raise FileNotFoundError(f"Missing source table: {AREAS_CSV}")
    with AREAS_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def source_flag(year: int, sensor: str, source_file: str) -> tuple[str, str, bool]:
    """Return (flag, caveat, include_in_strict_trend)."""
    if year == 2015 and "sentinel2_2015" in source_file:
        return (
            "sentinel2_toa_fallback",
            "Late-2015 annual TOA fallback; exclude from strict summer Sentinel-2 trend.",
            False,
        )
    if sensor == "Sentinel-2":
        return "sentinel2_sr", "", True
    if sensor == "Landsat":
        return (
            "landsat_historical",
            "Historical Landsat composite; lower spectral/channel compatibility than Sentinel-2.",
            True,
        )
    return "unknown", "Unknown source.", False


def quality_for_year(year: int, rows: list[dict[str, str]]) -> dict[str, str | int | float | bool]:
    first = rows[0]
    flag, caveat, strict = source_flag(year, first["sensor"], first["source_file"])
    methods = sorted({r["method"] for r in rows})
    has_rf = "RF" in methods
    has_unet = "U-Net" in methods
    has_ndsi = "NDSI" in methods

    score = 100
    if flag == "sentinel2_toa_fallback":
        score -= 35
    if flag == "landsat_historical":
        score -= 10
    if not has_rf:
        score -= 20
    if not has_unet:
        score -= 8
    if len(methods) < 2:
        score -= 10
    score = max(0, min(100, score))

    if score >= 85:
        confidence = "high"
    elif score >= 65:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "year": year,
        "sensor": first["sensor"],
        "source_file": first["source_file"],
        "source_flag": flag,
        "methods_available": ",".join(methods),
        "has_rf": has_rf,
        "has_unet": has_unet,
        "has_ndsi": has_ndsi,
        "quality_score": score,
        "confidence": confidence,
        "include_in_strict_trend": strict,
        "caveat": caveat,
    }


def choose_primary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    by_method = {r["method"]: r for r in rows}
    for method in METHOD_PRIORITY:
        if method in by_method:
            return by_method[method]
    return rows[0]


def git_or_snapshot_id() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def trend_summary(rows: list[dict[str, str]]) -> dict:
    strict = [r for r in rows if r["include_in_strict_trend"] == "True"]
    years = [int(r["year"]) for r in strict]
    areas = [safe_float(r["area_km2"]) for r in strict]
    valid = [(y, a) for y, a in zip(years, areas, strict=False) if np.isfinite(a)]
    if len(valid) < 3:
        return {"ok": False, "reason": "Need at least 3 valid strict-trend points."}
    years_arr = np.array([v[0] for v in valid], dtype=float)
    areas_arr = np.array([v[1] for v in valid], dtype=float)
    trend = metrics.trend_analysis(years_arr, areas_arr)
    future_years, predicted, ci_lower, ci_upper, _ = metrics.forecast_to_2050(years_arr, areas_arr)
    return {
        "ok": True,
        "method_preference": METHOD_PRIORITY,
        "n_years": len(valid),
        "years": [int(v[0]) for v in valid],
        "slope_km2_per_year": round(float(trend["slope_km2_per_year"]), 4),
        "r_squared": round(float(trend["r_squared"]), 4),
        "p_value": round(float(trend["p_value"]), 6),
        "significant": bool(trend["significant"]),
        "change_km2": round(float(trend["change_km2"]), 2),
        "change_percent": round(float(trend["change_percent"]), 2),
        "forecast_2050_km2": round(float(predicted[-1]), 2),
        "forecast_2050_ci95_lower": round(float(ci_lower[-1]), 2),
        "forecast_2050_ci95_upper": round(float(ci_upper[-1]), 2),
        "generated_forecast_years": [int(y) for y in future_years],
    }


def main() -> None:
    rows = read_area_rows()
    by_year: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_year.setdefault(int(row["year"]), []).append(row)

    quality_rows = [quality_for_year(year, year_rows) for year, year_rows in sorted(by_year.items())]
    quality_by_year = {int(r["year"]): r for r in quality_rows}

    decision_rows: list[dict[str, str | int | float | bool]] = []
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot_id = git_or_snapshot_id()
    for year, year_rows in sorted(by_year.items()):
        primary = choose_primary_row(year_rows)
        quality = quality_by_year[year]
        decision_rows.append(
            {
                "year": year,
                "area_km2": primary["area_km2"],
                "primary_method": primary["method"],
                "sensor": primary["sensor"],
                "source_flag": quality["source_flag"],
                "quality_score": quality["quality_score"],
                "confidence": quality["confidence"],
                "include_in_strict_trend": quality["include_in_strict_trend"],
                "source_file": primary["source_file"],
                "model_file": MODEL_FILES.get(primary["method"], "unknown"),
                "git_or_snapshot_id": snapshot_id,
                "caveat": quality["caveat"],
                "created_at": created_at,
            }
        )

    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with QUALITY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(quality_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(quality_rows)

    with DECISION_TS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(decision_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(decision_rows)

    summary = {
        "created_at": created_at,
        "quality_table": str(QUALITY_CSV.relative_to(ROOT)),
        "decision_timeseries_table": str(DECISION_TS_CSV.relative_to(ROOT)),
        "strict_trend": trend_summary([{k: str(v) for k, v in row.items()} for row in decision_rows]),
        "decision_readiness_notes": [
            "Use decision_ready_area_timeseries.csv for public reports, demos and pilot proposals.",
            "Use glacier_areas_all_years.csv for full research traceability.",
            "2015 is retained for transparency but excluded from strict trend by default.",
        ],
    }
    DECISION_SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(quality_rows)} quality rows -> {QUALITY_CSV}")
    print(f"Wrote {len(decision_rows)} decision time-series rows -> {DECISION_TS_CSV}")
    print(f"Wrote decision summary -> {DECISION_SUMMARY_JSON}")


if __name__ == "__main__":
    main()
