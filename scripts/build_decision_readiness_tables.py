#!/usr/bin/env python3
"""Build decision-ready time series and year quality tables.

The raw research tables keep every available prediction. Public reports and
pilot materials need a stricter view: explicit data-source flags, caveats, and
a clean trend subset that does not silently mix fallback imagery with standard
summer composites.
"""

from __future__ import annotations

import argparse
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
from src.temporal_quality import classify_annual_change  # noqa: E402

AREAS_CSV = config.TABLES_DIR / "glacier_areas_all_years.csv"
QUALITY_CSV = config.TABLES_DIR / "year_quality_scores.csv"
DECISION_TS_CSV = config.TABLES_DIR / "decision_ready_area_timeseries.csv"
DECISION_SUMMARY_JSON = config.RESULTS_DIR / "decision_readiness_summary.json"
SCENE_QUALITY_CSV = config.TABLES_DIR / "annual_scene_quality.csv"

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
            "Historical Landsat composite; exclude from strict Sentinel-2 trend because sensor and band schema differ.",
            False,
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
        "cloud_fraction": "",
        "shadow_fraction": "",
        "snow_fraction": "",
        "nodata_fraction": "",
        "temporal_status": "not_evaluated",
        "temporal_relative_change": "",
        "quality_score": score,
        "confidence": confidence,
        "include_in_strict_trend": strict,
        "caveat": caveat,
    }


def apply_scene_quality(
    quality_rows: list[dict[str, str | int | float | bool]],
) -> None:
    """Join measured scene QA and penalise missing or rejected evidence."""
    measured: dict[int, dict[str, str]] = {}
    if SCENE_QUALITY_CSV.is_file():
        with SCENE_QUALITY_CSV.open(newline="", encoding="utf-8") as handle:
            measured = {int(row["year"]): row for row in csv.DictReader(handle)}
    for quality in quality_rows:
        scene = measured.get(int(quality["year"]))
        if scene is None:
            quality["quality_score"] = max(0, int(quality["quality_score"]) - 20)
            caveat = str(quality["caveat"])
            quality["caveat"] = f"{caveat} Scene-level acquisition QA unavailable.".strip()
            continue
        for target, source in (
            ("cloud_fraction", "cloud_fraction"),
            ("shadow_fraction", "shadow_fraction"),
            ("snow_fraction", "snow_fraction"),
            ("nodata_fraction", "nodata_fraction"),
        ):
            quality[target] = scene.get(source, "")
        decision = scene.get("decision_status", "review")
        penalty = 30 if decision == "reject" else 10 if decision == "review" else 0
        quality["quality_score"] = max(0, int(quality["quality_score"]) - penalty)
        if decision == "reject":
            quality["include_in_strict_trend"] = False
        if decision != "accept":
            caveat = str(quality["caveat"])
            reason = scene.get("reason") or "scene QA requires review"
            quality["caveat"] = f"{caveat} Acquisition QA {decision}: {reason}.".strip()


def apply_temporal_quality_gate(
    quality_rows: list[dict[str, str | int | float | bool]],
    by_year: dict[int, list[dict[str, str]]],
) -> None:
    """Apply annual Sentinel-2 RF consistency without hiding rejected years."""
    quality_by_year = {int(row["year"]): row for row in quality_rows}
    comparable: list[tuple[int, float]] = []
    for year, rows in sorted(by_year.items()):
        quality = quality_by_year[year]
        if quality["source_flag"] != "sentinel2_sr":
            continue
        by_method = {row["method"]: row for row in rows}
        primary = by_method.get("RF") or by_method.get("U-Net") or by_method.get("NDSI")
        if primary is not None:
            comparable.append((year, float(primary["area_km2"])))

    previous_area: float | None = None
    for year, area in comparable:
        quality = quality_by_year[year]
        change = None if previous_area is None else abs(area - previous_area) / previous_area
        status, reason = classify_annual_change(change)
        quality["temporal_status"] = status
        quality["temporal_relative_change"] = "" if change is None else round(change, 6)
        penalty = {"baseline": 0, "normal": 0, "review": 10, "suspicious": 20, "reject": 40}[status]
        quality["quality_score"] = max(0, int(quality["quality_score"]) - penalty)
        if status == "reject":
            quality["include_in_strict_trend"] = False
        if status in {"review", "suspicious", "reject"}:
            caveat = str(quality["caveat"])
            quality["caveat"] = f"{caveat} {reason}.".strip()
        score = int(quality["quality_score"])
        quality["confidence"] = "high" if score >= 85 else "medium" if score >= 65 else "low"
        previous_area = area


def finalise_quality_confidence(quality_rows: list[dict[str, str | int | float | bool]]) -> None:
    for quality in quality_rows:
        score = int(quality["quality_score"])
        quality["confidence"] = "high" if score >= 85 else "medium" if score >= 65 else "low"


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


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main(
    *,
    quality_csv: Path = QUALITY_CSV,
    decision_ts_csv: Path = DECISION_TS_CSV,
    decision_summary_json: Path = DECISION_SUMMARY_JSON,
) -> None:
    rows = read_area_rows()
    by_year: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        by_year.setdefault(int(row["year"]), []).append(row)

    quality_rows = [quality_for_year(year, year_rows) for year, year_rows in sorted(by_year.items())]
    apply_scene_quality(quality_rows)
    apply_temporal_quality_gate(quality_rows, by_year)
    finalise_quality_confidence(quality_rows)
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

    for destination in (quality_csv, decision_ts_csv, decision_summary_json):
        destination.parent.mkdir(parents=True, exist_ok=True)
    with quality_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(quality_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(quality_rows)

    with decision_ts_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(decision_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(decision_rows)

    summary = {
        "created_at": created_at,
        "quality_table": _display_path(quality_csv),
        "decision_timeseries_table": _display_path(decision_ts_csv),
        "strict_trend": trend_summary([{k: str(v) for k, v in row.items()} for row in decision_rows]),
        "decision_readiness_notes": [
            "Use decision_ready_area_timeseries.csv for public reports, demos and pilot proposals.",
            "Use glacier_areas_all_years.csv for full research traceability.",
            "2015 is retained for transparency but excluded from strict trend by default.",
            "Historical Landsat rows are excluded from the strict Sentinel-2 trend because sensors and band schemas differ.",
            "The remaining trend is provisional until off-glacier snow QA and gold annotations are available.",
            "Any 2050 extrapolation remains exploratory and is not a climate projection.",
        ],
    }
    decision_summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(quality_rows)} quality rows -> {quality_csv}")
    print(f"Wrote {len(decision_rows)} decision time-series rows -> {decision_ts_csv}")
    print(f"Wrote decision summary -> {decision_summary_json}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir:
        main(
            quality_csv=args.output_dir / "year_quality_scores.csv",
            decision_ts_csv=args.output_dir / "decision_ready_area_timeseries.csv",
            decision_summary_json=args.output_dir / "decision_readiness_summary.json",
        )
    else:
        main()
