#!/usr/bin/env python3
"""Build a leakage-resistant glacier holdout manifest from metadata CSV."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_splits import cross_region_split, glacier_holdout_split  # noqa: E402


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
    manifest["ready"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {manifest['split_strategy']} manifest to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
