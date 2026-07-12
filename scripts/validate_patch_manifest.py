#!/usr/bin/env python3
"""Validate GlacierNET-KZ patch dataset manifests and split arrays."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

REQUIRED_ARRAYS = ("X_train.npy", "X_val.npy", "X_test.npy", "y_train.npy", "y_val.npy", "y_test.npy")


def load_shape(path: Path) -> tuple[tuple[int, ...], str]:
    arr = np.load(path, mmap_mode="r")
    return tuple(int(x) for x in arr.shape), str(arr.dtype)


def validate_manifest(path: Path, require_years: list[int] | None = None) -> list[str]:
    errors: list[str] = []
    manifest = json.loads(path.read_text(encoding="utf-8"))
    years = manifest.get("years")
    if not isinstance(years, list) or not years:
        return [f"{path}: manifest has no years"]
    expected_channels = int(manifest.get("channel_count", config.N_CHANNELS))
    if expected_channels < 1:
        return [f"{path}: channel_count must be positive"]

    seen_years: list[int] = []
    for entry in years:
        year = int(entry.get("year"))
        seen_years.append(year)
        if year == 2015:
            errors.append("2015 fallback must not be included in strict multi-year Sentinel-2 training manifests")
        for rel_key in ("source_file", "mask_file", "output_dir"):
            rel = entry.get(rel_key)
            if not rel or not (ROOT / rel).exists():
                errors.append(f"{year}: {rel_key} is missing or does not exist: {rel}")
        if int(entry.get("source_bands_loaded", 0)) != expected_channels:
            errors.append(f"{year}: source_bands_loaded must be {expected_channels}")
        output_dir = ROOT / str(entry.get("output_dir", ""))
        shapes: dict[str, tuple[int, ...]] = {}
        dtypes: dict[str, str] = {}
        for name in REQUIRED_ARRAYS:
            array_path = output_dir / name
            if not array_path.exists():
                errors.append(f"{year}: missing {array_path}")
                continue
            shapes[name], dtypes[name] = load_shape(array_path)

        for split in ("train", "val", "test"):
            x_name = f"X_{split}.npy"
            y_name = f"y_{split}.npy"
            if x_name not in shapes or y_name not in shapes:
                continue
            x_shape = shapes[x_name]
            y_shape = shapes[y_name]
            if len(x_shape) != 4 or x_shape[1:] != (config.PATCH_SIZE, config.PATCH_SIZE, expected_channels):
                errors.append(f"{year}: {x_name} has unexpected shape {x_shape}")
            if len(y_shape) != 3 or y_shape[1:] != (config.PATCH_SIZE, config.PATCH_SIZE):
                errors.append(f"{year}: {y_name} has unexpected shape {y_shape}")
            if x_shape[0] != y_shape[0]:
                errors.append(f"{year}: {split} X/y patch counts differ: {x_shape[0]} != {y_shape[0]}")

        counted_total = sum(shapes.get(f"X_{split}.npy", (0,))[0] for split in ("train", "val", "test"))
        if counted_total != int(entry.get("patches_total", -1)):
            errors.append(f"{year}: patches_total={entry.get('patches_total')} but arrays contain {counted_total}")
        if not (0.0 <= float(entry.get("glacier_pixel_fraction", -1.0)) <= 1.0):
            errors.append(f"{year}: glacier_pixel_fraction outside [0, 1]")
        if entry.get("split_strategy") == "random_patch_split" and "split_leakage_warning" not in entry:
            errors.append(f"{year}: random split must carry split_leakage_warning")

    if require_years is not None and sorted(seen_years) != sorted(require_years):
        errors.append(f"manifest years {sorted(seen_years)} != required years {sorted(require_years)}")

    if manifest.get("split_strategy") == "year_holdout":
        errors.extend(validate_year_holdout(manifest, seen_years))

    return errors


def validate_year_holdout(manifest: dict, manifest_years: list[int]) -> list[str]:
    errors: list[str] = []
    split_years: dict[str, set[int]] = {}
    for split in ("train", "val", "test"):
        raw_years = manifest.get(f"{split}_years")
        if not isinstance(raw_years, list) or not raw_years:
            errors.append(f"year_holdout manifest requires non-empty {split}_years")
            split_years[split] = set()
            continue
        try:
            split_years[split] = {int(year) for year in raw_years}
        except (TypeError, ValueError):
            errors.append(f"{split}_years must contain integer years")
            split_years[split] = set()

    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = split_years[left] & split_years[right]
        if overlap:
            errors.append(f"year_holdout {left}_years and {right}_years overlap: {sorted(overlap)}")

    assigned_years = set().union(*split_years.values())
    expected_years = set(manifest_years)
    if assigned_years != expected_years:
        errors.append(
            "year_holdout split years must exactly cover manifest years: "
            f"assigned={sorted(assigned_years)}, manifest={sorted(expected_years)}"
        )
    if "temporal_split_note" not in manifest:
        errors.append("year_holdout manifest requires temporal_split_note")
    return errors


def parse_years(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    years: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            years.extend(range(start, end + 1))
        else:
            years.append(int(part))
    return sorted(dict.fromkeys(years))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--require-years", default=None, help="Comma/range list that must match manifest years")
    args = parser.parse_args()

    errors = validate_manifest(args.manifest, parse_years(args.require_years))
    if errors:
        print("PATCH MANIFEST VALIDATION FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Patch manifest validation passed: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
