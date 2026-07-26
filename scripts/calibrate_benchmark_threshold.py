#!/usr/bin/env python3
"""Calibrate a fixed benchmark threshold on validation arrays only."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.benchmark_metrics import calibrate_threshold  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-labels", type=Path, required=True)
    parser.add_argument("--validation-probabilities", type=Path, required=True)
    parser.add_argument("--pixel-area-m2", type=float, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    result = calibrate_threshold(
        np.load(args.validation_labels),
        np.load(args.validation_probabilities),
        pixel_area_m2=args.pixel_area_m2,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["sweep"][0]))
        writer.writeheader()
        writer.writerows(result["sweep"])
    print(f"Selected validation threshold: {result['selected_threshold']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
