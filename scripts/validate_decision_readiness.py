#!/usr/bin/env python3
"""Validate decision-ready GlacierNET-KZ tables against raw data and provenance."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

AREAS_CSV = config.TABLES_DIR / "glacier_areas_all_years.csv"
QUALITY_CSV = config.TABLES_DIR / "year_quality_scores.csv"
DECISION_TS_CSV = config.TABLES_DIR / "decision_ready_area_timeseries.csv"
SUMMARY_JSON = config.RESULTS_DIR / "decision_readiness_summary.json"

REQUIRED_DECISION_COLUMNS = {
    "year",
    "area_km2",
    "primary_method",
    "sensor",
    "source_flag",
    "quality_score",
    "confidence",
    "include_in_strict_trend",
    "source_file",
    "model_file",
    "git_or_snapshot_id",
    "caveat",
    "created_at",
}
ALLOWED_FLAGS = {"landsat_historical", "sentinel2_sr", "sentinel2_toa_fallback"}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def expected_source_flag(year: int, sensor: str, source_file: str) -> str:
    if year == 2015 and source_file.endswith("sentinel2_2015.tif"):
        return "sentinel2_toa_fallback"
    if sensor == "Sentinel-2":
        return "sentinel2_sr"
    if sensor == "Landsat":
        return "landsat_historical"
    return "unknown"


def raw_source_exists(year: int) -> bool:
    return (config.DATA_RAW_SENTINEL2 / f"sentinel2_{year}.tif").exists() or (
        config.DATA_RAW_LANDSAT / f"landsat_{year}.tif"
    ).exists()


def rel_exists(path_value: str) -> bool:
    return bool(path_value) and (ROOT / path_value).exists()


def model_reference_ok(path_value: str) -> bool:
    return path_value.startswith("spectral_index:") or rel_exists(path_value)


def main() -> int:
    errors: list[str] = []
    try:
        areas = read_csv(AREAS_CSV)
        quality = read_csv(QUALITY_CSV)
        decision = read_csv(DECISION_TS_CSV)
        summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"DECISION READINESS VALIDATION FAILED: {error}")
        return 1

    if not decision:
        errors.append("decision_ready_area_timeseries.csv has no rows")
    else:
        missing_columns = REQUIRED_DECISION_COLUMNS - set(decision[0])
        if missing_columns:
            errors.append(f"decision table missing columns: {sorted(missing_columns)}")

    quality_by_year = {int(row["year"]): row for row in quality}
    areas_by_year_method = {(int(row["year"]), row["method"]): row for row in areas}
    decision_years: list[int] = []

    for row in decision:
        year = int(row["year"])
        decision_years.append(year)
        if not raw_source_exists(year):
            errors.append(f"{year}: no raw source file exists")
        if not rel_exists(row["source_file"]):
            errors.append(f"{year}: source_file does not exist: {row['source_file']}")
        if row["source_flag"] not in ALLOWED_FLAGS:
            errors.append(f"{year}: unsupported source_flag={row['source_flag']}")
        expected_flag = expected_source_flag(year, row["sensor"], row["source_file"])
        if row["source_flag"] != expected_flag:
            errors.append(f"{year}: source_flag={row['source_flag']} expected {expected_flag}")
        if year == 2015 and row["include_in_strict_trend"] != "False":
            errors.append("2015 Sentinel-2 TOA fallback must be excluded from strict trend")
        if year != 2015 and row["include_in_strict_trend"] != "True":
            errors.append(f"{year}: expected include_in_strict_trend=True")
        if not model_reference_ok(row["model_file"]):
            errors.append(f"{year}: model_file is not resolvable: {row['model_file']}")
        if not row["git_or_snapshot_id"]:
            errors.append(f"{year}: git_or_snapshot_id is empty")

        q = quality_by_year.get(year)
        if not q:
            errors.append(f"{year}: missing quality row")
        else:
            for field in ("source_file", "source_flag", "quality_score", "confidence", "include_in_strict_trend"):
                if row[field] != q[field]:
                    errors.append(f"{year}: decision {field}={row[field]!r} != quality {q[field]!r}")

        source = areas_by_year_method.get((year, row["primary_method"]))
        if not source:
            errors.append(f"{year}: primary_method={row['primary_method']} missing from glacier_areas_all_years.csv")
        elif row["area_km2"] != source["area_km2"]:
            errors.append(f"{year}: area_km2={row['area_km2']} != source area={source['area_km2']}")

    strict_years = [int(row["year"]) for row in decision if row["include_in_strict_trend"] == "True"]
    summary_years = summary.get("strict_trend", {}).get("years", [])
    if strict_years != summary_years:
        errors.append(f"strict trend years mismatch: table={strict_years} summary={summary_years}")
    if 2015 in summary_years:
        errors.append("decision_readiness_summary strict trend includes 2015 fallback")

    if sorted(decision_years) != decision_years:
        errors.append("decision rows are not sorted by year")

    if errors:
        print("DECISION READINESS VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Decision readiness validation passed.")
    print(f"Validated {len(decision)} decision rows and {len(strict_years)} strict-trend years.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
