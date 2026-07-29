#!/usr/bin/env python3
"""Validate cascade benchmark structure and fail closed on missing evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "benchmarks/central_asia_cascade"
REQUIRED_DOCS = ("protocol.md", "dataset_card.md")
REQUIRED_TABLES = {
    "basin_ranking.csv": {
        "snapshot_id",
        "basin_id",
        "split",
        "rank",
        "attention_score",
        "relevant_event",
        "cutoff_time",
        "model_version",
    },
    "event_replay.csv": {
        "event_id",
        "basin_id",
        "split",
        "event_time",
        "lead_time_days",
        "cutoff_time",
        "abstained",
        "selected_for_review",
        "warning_time",
        "manifest_sha256",
    },
    "observation_value.csv": {
        "snapshot_id",
        "basin_id",
        "action_id",
        "predicted_voi",
        "selected",
        "realised_loss_reduction",
        "action_cost",
        "latency_hours",
    },
    "resilience_replay.csv": {
        "snapshot_id",
        "basin_id",
        "event_id",
        "split",
        "cutoff_time",
        "baseline_area_rank",
        "static_susceptibility_rank",
        "risk_twin_rank",
        "resilience_twin_rank",
        "model_margin",
        "margin_right_censored",
        "failure_genome",
        "lead_time_days",
        "false_alert",
        "abstained",
        "model_version",
    },
}
ALLOWED_SPLITS = {"development", "temporal_test", "external_test"}
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        errors.append(f"invalid JSON at {path.relative_to(ROOT)}: {error}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"JSON root must be an object: {path.relative_to(ROOT)}")
        return {}
    return payload


def _valid_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_records(records: list[Any], *, controls: bool, errors: list[str]) -> None:
    seen_events: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"{'non_event_controls' if controls else 'events'}[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        required = {
            "event_id",
            "basin_id",
            "region",
            "event_type",
            "event_time",
            "event_time_precision",
            "verification_status",
            "sources",
            "split",
            "observation_snapshot",
        }
        missing = sorted(required - set(record))
        if missing:
            errors.append(f"{prefix} missing fields: {', '.join(missing)}")
            continue
        event_id = str(record["event_id"])
        if not event_id or event_id in seen_events:
            errors.append(f"{prefix} event_id must be non-empty and unique")
        seen_events.add(event_id)
        if record["split"] not in ALLOWED_SPLITS:
            errors.append(f"{prefix} has invalid split")
        expected_type = "non_event_control" if controls else None
        if expected_type and record["event_type"] != expected_type:
            errors.append(f"{prefix} must use event_type=non_event_control")
        if not _valid_datetime(record["event_time"]):
            errors.append(f"{prefix} has invalid event_time")
        sources = record["sources"]
        if not isinstance(sources, list) or not sources:
            errors.append(f"{prefix} requires at least one source")
        snapshot = record["observation_snapshot"]
        if not isinstance(snapshot, dict):
            errors.append(f"{prefix} observation_snapshot must be an object")
        else:
            if not SHA256.fullmatch(str(snapshot.get("sha256", ""))):
                errors.append(f"{prefix} snapshot requires a lowercase SHA-256")
            if not _valid_datetime(snapshot.get("cutoff_time")):
                errors.append(f"{prefix} snapshot has invalid cutoff_time")
            elif _valid_datetime(record["event_time"]):
                cutoff = datetime.fromisoformat(str(snapshot["cutoff_time"]).replace("Z", "+00:00"))
                event_time = datetime.fromisoformat(str(record["event_time"]).replace("Z", "+00:00"))
                if cutoff > event_time:
                    errors.append(f"{prefix} snapshot cutoff occurs after event time")


def validate(*, allow_incomplete: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    blockers: list[str] = []
    for name in REQUIRED_DOCS:
        path = BENCHMARK / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing benchmark document: {path.relative_to(ROOT)}")

    schema = _read_json(BENCHMARK / "schemas/basin_event.schema.json", errors)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("basin event schema must declare JSON Schema draft 2020-12")

    for name, required_header in REQUIRED_TABLES.items():
        path = BENCHMARK / "tables" / name
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                header = set(next(csv.reader(handle), []))
        except FileNotFoundError:
            errors.append(f"missing benchmark table: {path.relative_to(ROOT)}")
            continue
        if header != required_header:
            errors.append(f"invalid header in {path.relative_to(ROOT)}")

    manifest = _read_json(BENCHMARK / "manifests/event_replay.json", errors)
    events = manifest.get("events", [])
    controls = manifest.get("non_event_controls", [])
    if not isinstance(events, list) or not isinstance(controls, list):
        errors.append("events and non_event_controls must be arrays")
    else:
        _validate_records(events, controls=False, errors=errors)
        _validate_records(controls, controls=True, errors=errors)

        basin_splits: dict[str, set[str]] = {}
        for record in [*events, *controls]:
            if isinstance(record, dict) and record.get("basin_id") and record.get("split"):
                basin_splits.setdefault(str(record["basin_id"]), set()).add(str(record["split"]))
        overlapping = sorted(basin for basin, splits in basin_splits.items() if len(splits) > 1)
        if overlapping:
            errors.append("basin leakage across splits: " + ", ".join(overlapping))

    if manifest.get("ready_for_scientific_claims") is not True:
        reasons = manifest.get("blocked_reasons", [])
        blockers.extend(str(reason) for reason in reasons if str(reason).strip())
        if not blockers:
            blockers.append("manifest is not ready and gives no blocked reasons")
    elif not events or not controls:
        errors.append("ready manifest requires both verified events and non-event controls")
    else:
        present_splits = {str(record.get("split")) for record in [*events, *controls] if isinstance(record, dict)}
        missing_splits = ALLOWED_SPLITS - present_splits
        if missing_splits:
            errors.append("ready manifest missing splits: " + ", ".join(sorted(missing_splits)))

    if blockers and not allow_incomplete:
        errors.extend(f"cascade benchmark evidence blocker: {blocker}" for blocker in blockers)
    return errors, blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Validate structure while reporting, but not failing on, missing retrospective evidence.",
    )
    args = parser.parse_args()
    errors, blockers = validate(allow_incomplete=args.allow_incomplete)
    for blocker in blockers:
        print(f"BLOCKED: {blocker}")
    if errors:
        print("CASCADE BENCHMARK VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1
    status = "STRUCTURE VALID; EVIDENCE INCOMPLETE" if blockers else "BENCHMARK READY"
    print(f"Central Asia Cascade Benchmark: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
