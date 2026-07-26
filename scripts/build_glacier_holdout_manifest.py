#!/usr/bin/env python3
"""Build a leakage-resistant glacier holdout manifest from metadata CSV."""

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

from src.benchmark_splits import cross_region_split, glacier_holdout_split  # noqa: E402

REQUIRED_GOLD_FIELDS = {
    "glacier_id",
    "region",
    "year",
    "annotator_a",
    "annotator_b",
    "adjudicator",
    "annotation_status",
    "label_sha256",
}


def validate_gold_rows(rows: list[dict[str, str]]) -> None:
    missing = REQUIRED_GOLD_FIELDS - set(rows[0])
    if missing:
        raise ValueError("gold metadata missing columns: " + ", ".join(sorted(missing)))
    for index, row in enumerate(rows, start=2):
        if row["annotation_status"].strip() != "adjudicated":
            raise ValueError(f"row {index}: annotation_status must be adjudicated")
        annotators = {row["annotator_a"].strip(), row["annotator_b"].strip()}
        if "" in annotators or len(annotators) != 2:
            raise ValueError(f"row {index}: two distinct independent annotators are required")
        if not row["adjudicator"].strip():
            raise ValueError(f"row {index}: adjudicator is required")
        digest = row["label_sha256"].strip().lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError(f"row {index}: label_sha256 must be a lowercase SHA-256")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True, help="CSV with glacier_id and optional region")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-region")
    parser.add_argument("--test-region")
    args = parser.parse_args()

    with args.metadata.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "glacier_id" not in rows[0]:
        raise ValueError("metadata CSV must contain glacier_id")
    validate_gold_rows(rows)
    if bool(args.train_region) != bool(args.test_region):
        raise ValueError("--train-region and --test-region must be provided together")
    if args.train_region:
        if "region" not in rows[0]:
            raise ValueError("cross-region mode requires a region column")
        regions = {row["glacier_id"].strip(): row["region"].strip() for row in rows}
        manifest = cross_region_split(
            regions,
            train_region=args.train_region,
            test_region=args.test_region,
        )
    else:
        manifest = glacier_holdout_split((row["glacier_id"] for row in rows), seed=args.seed)
    manifest["source_metadata"] = str(args.metadata)
    manifest["source_metadata_sha256"] = hashlib.sha256(args.metadata.read_bytes()).hexdigest()
    manifest["label_quality_tier"] = "gold"
    manifest["annotation_protocol"] = "two_independent_annotators_plus_adjudication"
    manifest["annotated_glacier_year_rows"] = len(rows)
    manifest["ready"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['split_strategy']} manifest to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
