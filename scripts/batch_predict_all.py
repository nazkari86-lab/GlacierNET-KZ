#!/usr/bin/env python3
"""Run predict.py for every year with raw data but missing saved predictions."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from predict import list_available_years
from src import config


def years_needing_predictions(require_mask: str = "rf_mask.tif") -> list[int]:
    """Return years that have raw TIF but lack the requested mask file."""
    available = {y["year"] for y in list_available_years()}
    pred_dir = ROOT / "predictions"
    missing: list[int] = []
    for year in sorted(available):
        mask_path = pred_dir / str(year) / require_mask
        if not mask_path.exists():
            missing.append(year)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch inference for all missing years")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["ndsi", "rf", "unet"],
        choices=["ndsi", "rf", "unet"],
    )
    parser.add_argument("--skip-unet", action="store_true", help="Skip U-Net (faster)")
    parser.add_argument("--years", nargs="*", type=int, help="Explicit years (default: auto-detect)")
    parser.add_argument("--force", action="store_true", help="Re-run even if masks exist")
    args = parser.parse_args()

    models = [m for m in args.models if not (args.skip_unet and m == "unet")]

    if args.years:
        targets = sorted(args.years)
    elif args.force:
        targets = sorted({y["year"] for y in list_available_years()})
    else:
        targets = years_needing_predictions()

    if not targets:
        print("All years already have predictions.")
        return

    print(f"Years to process ({len(targets)}): {targets}")
    print(f"Models: {models}")

    failed: list[int] = []
    for i, year in enumerate(targets, 1):
        print(f"\n{'=' * 60}\n[{i}/{len(targets)}] Year {year}\n{'=' * 60}")
        cmd = [
            sys.executable,
            str(ROOT / "predict.py"),
            "--year",
            str(year),
            "--save",
            "--models",
            *models,
        ]
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        if rc != 0:
            print(f"  FAILED year {year} (exit {rc})")
            failed.append(year)

    print(f"\nDone. Failed years: {failed or 'none'}")

    # Refresh downstream artifacts
    for script in ("rebuild_areas_table.py", "pipeline_status.py"):
        path = ROOT / "scripts" / script
        if path.exists():
            subprocess.run([sys.executable, str(path)], cwd=str(ROOT), check=False)


if __name__ == "__main__":
    main()
