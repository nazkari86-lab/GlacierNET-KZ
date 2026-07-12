#!/usr/bin/env python3
"""Create a temporal year-held-out manifest without duplicating patch arrays."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_multiyear_patches import parse_years  # noqa: E402


def validate_partition(source_years: set[int], splits: dict[str, list[int]]) -> None:
    split_sets = {name: set(years) for name, years in splits.items()}
    if not all(split_sets.values()):
        raise ValueError("train, validation, and test year lists must each be non-empty")
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = split_sets[left] & split_sets[right]
        if overlap:
            raise ValueError(f"{left} and {right} years overlap: {sorted(overlap)}")
    assigned = set().union(*split_sets.values())
    if assigned != source_years:
        raise ValueError(
            "year partition must exactly cover source years: "
            f"assigned={sorted(assigned)}, source={sorted(source_years)}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-years", default="2016-2022")
    parser.add_argument("--val-years", default="2023")
    parser.add_argument("--test-years", default="2024")
    args = parser.parse_args()

    source_path = args.source_manifest.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    entries = source.get("years")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"Source manifest has no years: {source_path}")

    source_years = {int(entry["year"]) for entry in entries}
    splits = {
        "train": parse_years(args.train_years),
        "val": parse_years(args.val_years),
        "test": parse_years(args.test_years),
    }
    validate_partition(source_years, splits)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_role": "temporal_year_holdout_evaluation",
        "split_strategy": "year_holdout",
        "source_manifest": str(source_path.relative_to(ROOT)),
        "years_requested": sorted(source_years),
        "excluded_years": source.get("excluded_years", []),
        "train_years": splits["train"],
        "val_years": splits["val"],
        "test_years": splits["test"],
        "temporal_split_note": (
            "Each calendar year is assigned to exactly one split. src.train loads all "
            "pre-existing patch shards from that year into the assigned split, so no "
            "patch from a validation or test year can enter training."
        ),
        "notes": [
            "This manifest reuses patch arrays from the source manifest and adds no duplicate arrays.",
            "2015 remains excluded because it is a late-year Sentinel-2 TOA fallback.",
            "The capped source dataset is suitable for a temporal validation smoke run, not final scientific claims.",
        ],
        "years": entries,
    }
    if "channel_count" in source:
        manifest["channel_count"] = source["channel_count"]
    if "feature_schema" in source:
        manifest["feature_schema"] = source["feature_schema"]
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote year-held-out manifest -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
