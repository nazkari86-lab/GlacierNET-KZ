#!/usr/bin/env python3
"""Validate that a year-holdout manifest has no split leakage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    splits = {key: {int(v) for v in manifest.get(key, [])} for key in ("train_years", "val_years", "test_years")}
    for left, right in (("train_years", "val_years"), ("train_years", "test_years"), ("val_years", "test_years")):
        overlap = splits[left] & splits[right]
        if overlap:
            errors.append(f"{left} and {right} overlap: {sorted(overlap)}")
    assigned = set().union(*splits.values())
    manifest_years = {int(item["year"]) for item in manifest.get("years", []) if "year" in item}
    if manifest_years and assigned != manifest_years:
        errors.append(f"split years {sorted(assigned)} do not cover manifest years {sorted(manifest_years)}")
    if not manifest.get("temporal_split_note"):
        errors.append("temporal_split_note is required")
    if errors:
        print("YEAR HOLDOUT VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Year holdout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
