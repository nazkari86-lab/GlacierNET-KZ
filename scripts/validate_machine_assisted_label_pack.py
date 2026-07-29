#!/usr/bin/env python3
"""Fail closed when a machine-assisted RGI label pack is malformed or mislabelled."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "benchmarks/v2/annotations/machine_assisted")
    args = parser.parse_args()
    directory = args.directory.resolve()
    manifest_path = directory / "manifest.json"
    queue_path = directory / "machine_assisted_annotation_queue.csv"
    errors: list[str] = []
    if not manifest_path.is_file() or not queue_path.is_file():
        raise FileNotFoundError("machine-assisted manifest or queue is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "glaciernet-kz.machine-assisted-label-pack.v1":
        errors.append("unexpected manifest schema")
    prohibited = set(manifest.get("prohibited_claims", []))
    if "independent expert gold-label accuracy" not in prohibited:
        errors.append("manifest must explicitly prohibit gold-accuracy claim")
    queue_info = manifest.get("queue", {})
    if queue_info.get("sha256") != digest(queue_path):
        errors.append("queue checksum mismatch")
    with queue_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 54:
        errors.append(f"expected 54 queue rows, got {len(rows)}")
    if any(row.get("label_tier") != "machine_assisted_rgi_inventory" for row in rows):
        errors.append("every row must remain machine-assisted")
    if any(row.get("annotation_status") != "provisional_not_gold" for row in rows):
        errors.append("every row must remain provisional_not_gold")
    if any(row.get("human_review_status") != "not_reviewed" for row in rows):
        errors.append("machine-assisted rows cannot be marked human-reviewed")
    records = manifest.get("label_records", [])
    if len(records) != 3:
        errors.append("expected one GeoPackage record for each of three years")
    else:
        import geopandas as gpd

        for record in records:
            path = ROOT / record["path"]
            if not path.is_file():
                errors.append(f"missing label file: {record['path']}")
                continue
            if record.get("sha256") != digest(path):
                errors.append(f"label checksum mismatch: {record['path']}")
                continue
            frame = gpd.read_file(path, layer="glacier_labels")
            if len(frame) != 18 or not frame.geometry.is_valid.all() or frame.geometry.is_empty.any():
                errors.append(f"invalid geometries or feature count in {record['path']}")
            if set(frame.get("label_tier", [])) != {"machine_assisted_rgi_inventory"}:
                errors.append(f"incorrect label tier in {record['path']}")
            if set(frame.get("human_review_status", [])) != {"not_reviewed"}:
                errors.append(f"incorrect review status in {record['path']}")
    if errors:
        print("MACHINE-ASSISTED LABEL PACK INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Machine-assisted label pack valid; it remains explicitly non-gold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
