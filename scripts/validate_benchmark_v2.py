#!/usr/bin/env python3
"""Validate benchmark v2 structure and fail closed on missing scientific evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_splits import validate_group_manifest  # noqa: E402

BENCHMARK = ROOT / "benchmarks/v2"
REQUIRED_DOCS = ("protocol.md", "dataset_card.md", "annotation_guidelines.md")
REQUIRED_TABLES = (
    "metrics_summary.csv",
    "per_glacier_metrics.csv",
    "area_errors.csv",
    "bootstrap_intervals.csv",
)


def validate(*, allow_incomplete: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    blockers: list[str] = []
    for name in REQUIRED_DOCS:
        path = BENCHMARK / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing benchmark document: {path.relative_to(ROOT)}")
    for name in REQUIRED_TABLES:
        path = BENCHMARK / "tables" / name
        if not path.is_file():
            errors.append(f"missing benchmark table: {path.relative_to(ROOT)}")
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
            if not rows or not rows[0]:
                errors.append(f"benchmark table has no header: {path.relative_to(ROOT)}")
            if name == "metrics_summary.csv" and len(rows) < 2:
                errors.append("metrics_summary.csv must contain the completed one-AOI silver evidence rows")

    temporal_path = BENCHMARK / "manifests/temporal_holdout.json"
    try:
        temporal = json.loads(temporal_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        errors.append(f"invalid temporal manifest: {error}")
    else:
        groups = [set(temporal.get(key, [])) for key in ("train_years", "validation_years", "test_years")]
        if any(not group for group in groups):
            errors.append("temporal holdout requires non-empty train/validation/test years")
        if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
            errors.append("temporal holdout years overlap")
        if temporal.get("label_quality_tier") != "silver":
            errors.append("current temporal holdout must remain labelled silver")

    for name, require_validation in (("glacier_holdout.json", True), ("cross_region.json", False)):
        path = BENCHMARK / "manifests" / name
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as error:
            errors.append(f"invalid {name}: {error}")
            continue
        if manifest.get("ready") is not True:
            blockers.append(f"{name}: {manifest.get('blocked_reason', 'not ready')}")
            continue
        try:
            validate_group_manifest(manifest, require_validation=require_validation)
        except ValueError as error:
            errors.append(f"{name}: {error}")

    anomaly_path = ROOT / "results/tables/temporal_anomalies.csv"
    if not anomaly_path.is_file():
        errors.append("missing results/tables/temporal_anomalies.csv")
    else:
        with anomaly_path.open(newline="", encoding="utf-8") as handle:
            anomalies = list(csv.DictReader(handle))
        rejected = {int(row["year"]) for row in anomalies if row.get("status") == "reject"}
        if 2018 not in rejected:
            errors.append("2018 must be rejected by the current RF temporal gate")

    quality_path = ROOT / "results/tables/year_quality_scores.csv"
    if not quality_path.is_file():
        errors.append("missing year_quality_scores.csv")
    else:
        with quality_path.open(newline="", encoding="utf-8") as handle:
            quality = {int(row["year"]): row for row in csv.DictReader(handle)}
        row_2018 = quality.get(2018, {})
        if row_2018.get("temporal_status") != "reject":
            errors.append("2018 quality record must carry temporal_status=reject")
        if int(row_2018.get("quality_score", 101)) >= 100:
            errors.append("2018 physically suspicious result cannot have quality_score=100")

    safeguard_path = BENCHMARK / "provisional/inventory_guided_decoder_2024.json"
    try:
        safeguard = json.loads(safeguard_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        errors.append(f"invalid inventory-guided safeguard report: {error}")
    else:
        if safeguard.get("schema") != "glaciernet-kz.inventory-guided-external-safeguard.v1":
            errors.append("invalid inventory-guided safeguard schema")
        replay = safeguard.get("external_replay", {})
        if replay.get("parameters_frozen_before_external_replay") is not True:
            errors.append("inventory-guided parameters must be frozen before external replay")
        if replay.get("n_glaciers") != 9:
            errors.append("inventory-guided external replay must retain the frozen nine-glacier cohort")
        deltas = replay.get("paired_delta_decoder_minus_unconstrained_model", {})
        if float(deltas.get("hard_dice", {}).get("ci_lower", -1)) <= 0:
            errors.append("inventory-guided Dice improvement interval must remain above zero")
        if float(deltas.get("absolute_area_error_percent", {}).get("ci_upper", 1)) >= 0:
            errors.append("inventory-guided absolute-area-error interval must remain below zero")
        table_relative = safeguard.get("artifacts", {}).get("external_table", "")
        table_path = ROOT / str(table_relative)
        if not table_path.is_file():
            errors.append("inventory-guided per-glacier table is missing")
        else:
            digest = hashlib.sha256(table_path.read_bytes()).hexdigest()
            if digest != safeguard.get("artifacts", {}).get("external_table_sha256"):
                errors.append("inventory-guided per-glacier table digest mismatch")
        forbidden = set(safeguard.get("claims_not_allowed", []))
        if "independent external-region accuracy" not in forbidden:
            errors.append("inventory-guided report must block independent external accuracy claims")

    if blockers and not allow_incomplete:
        errors.extend(f"benchmark evidence blocker: {blocker}" for blocker in blockers)
    return errors, blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Validate structure while reporting, but not failing on, missing gold/cross-region evidence.",
    )
    args = parser.parse_args()
    errors, blockers = validate(allow_incomplete=args.allow_incomplete)
    for blocker in blockers:
        print(f"BLOCKED: {blocker}")
    if errors:
        print("BENCHMARK V2 VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    status = "STRUCTURE VALID; EVIDENCE INCOMPLETE" if blockers else "BENCHMARK READY"
    print(f"Benchmark v2: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
