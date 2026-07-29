#!/usr/bin/env python3
"""Fail-closed validation for the enhanced provisional training dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "data/processed/patches/enhanced_provisional_spatial_holdout"
SCHEMA = "glaciernet-kz.enhanced-provisional-training.v1"
SPLITS = ("train", "val", "test")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(directory: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return [f"Missing manifest: {manifest_path}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        errors.append(f"Unexpected schema: {manifest.get('schema')}")
    if manifest.get("annotation_status") != "provisional_not_gold":
        errors.append("Dataset must remain explicitly provisional_not_gold")
    if manifest.get("split_strategy") != "glacier_group_spatial_holdout":
        errors.append("Dataset must use glacier_group_spatial_holdout")
    if manifest.get("dataset_role") != "machine_assisted_training_only_not_gold_benchmark":
        errors.append("Dataset role must prohibit gold-benchmark use")
    if manifest.get("eligible_confidence") != "high_provisional":
        errors.append("Only high_provisional labels may be eligible")

    outputs = {entry["path"]: entry for entry in manifest.get("outputs", [])}
    split_glaciers: dict[str, set[str]] = {}
    metadata: dict[str, pd.DataFrame] = {}
    total_patches = 0
    for split in SPLITS:
        x_path = directory / f"X_{split}.npy"
        y_path = directory / f"y_{split}.npy"
        w_path = directory / f"w_{split}.npy"
        meta_path = directory / f"metadata_{split}.csv"
        for path in (x_path, y_path, w_path, meta_path):
            if not path.is_file():
                errors.append(f"Missing {path}")
        if any(not path.is_file() for path in (x_path, y_path, w_path, meta_path)):
            continue

        x = np.load(x_path, mmap_mode="r")
        y = np.load(y_path, mmap_mode="r")
        weights = np.load(w_path, mmap_mode="r")
        frame = pd.read_csv(meta_path)
        metadata[split] = frame
        total_patches += len(x)
        if x.dtype != np.float16 or x.ndim != 4 or x.shape[1:] != (256, 256, 11):
            errors.append(f"{split}: unexpected X shape/dtype {x.shape}/{x.dtype}")
        if y.dtype != np.uint8 or y.shape != x.shape[:3]:
            errors.append(f"{split}: unexpected y shape/dtype {y.shape}/{y.dtype}")
        if weights.dtype != np.float16 or weights.shape != y.shape:
            errors.append(f"{split}: unexpected weight shape/dtype {weights.shape}/{weights.dtype}")
        if len(frame) != len(x):
            errors.append(f"{split}: metadata count {len(frame)} != patch count {len(x)}")
        if not np.isin(np.unique(y), [0, 1]).all():
            errors.append(f"{split}: labels must be binary")
        if np.any(np.asarray(y).reshape(len(y), -1).sum(axis=1) == 0):
            errors.append(f"{split}: every retained patch must contain glacier pixels")
        if float(weights.min()) < 0 or float(weights.max()) > 1:
            errors.append(f"{split}: weights outside [0, 1]")
        if (frame.get("confidence") != "high_provisional").any():
            errors.append(f"{split}: non-high provisional metadata found")
        split_glaciers[split] = set(frame["glacier_id"].astype(str))
        declared = set(manifest.get("splits", {}).get(split, {}).get("glaciers", []))
        if split_glaciers[split] != declared:
            errors.append(f"{split}: manifest glacier IDs differ from metadata")
        if int(manifest.get("splits", {}).get(split, {}).get("patch_count", -1)) != len(x):
            errors.append(f"{split}: manifest patch_count differs from arrays")

    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = split_glaciers.get(left, set()) & split_glaciers.get(right, set())
        if overlap:
            errors.append(f"Glacier leakage between {left}/{right}: {sorted(overlap)}")

    # Fail if any source-space patch footprint overlaps across splits, even if
    # its glacier IDs differ. This catches accidental spatial context leakage.
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        if left not in metadata or right not in metadata:
            continue
        left_boxes = [(row.year, box(row.left, row.bottom, row.right, row.top)) for row in metadata[left].itertuples()]
        right_boxes = [
            (row.year, box(row.left, row.bottom, row.right, row.top)) for row in metadata[right].itertuples()
        ]
        if any(a.intersects(b) for _, a in left_boxes for _, b in right_boxes):
            errors.append(f"Spatial patch-footprint leakage between {left}/{right}")

    coverage_path = directory / "coverage.csv"
    if coverage_path.is_file():
        coverage = pd.read_csv(coverage_path)
        if len(coverage) != int(manifest.get("eligible_tasks", -1)):
            errors.append("Coverage rows must match eligible annotation tasks")
        if float(coverage["geometry_coverage"].min()) < 0.995:
            errors.append(f"Geometry coverage below 99.5%: {coverage['geometry_coverage'].min():.4f}")
        if (coverage["patches"] < 1).any():
            errors.append("Every eligible annotation must produce at least one patch")
    else:
        errors.append("Missing coverage.csv")

    if total_patches != sum(int(value.get("patch_count", 0)) for value in manifest.get("splits", {}).values()):
        errors.append("Total patch count differs from split summaries")
    if int(manifest.get("excluded_tasks", {}).get("total", -1)) <= 0:
        errors.append("Excluded medium/low review tasks must be recorded")
    qa_path = ROOT / str(manifest.get("qa_preview", {}).get("path", ""))
    if not qa_path.is_file() or qa_path.stat().st_size < 10_000:
        errors.append("Missing or implausibly small training QA preview")
    if {case.get("split") for case in manifest.get("qa_preview", {}).get("cases", [])} != set(SPLITS):
        errors.append("Training QA preview must contain one case per split")

    for relative_path, entry in outputs.items():
        path = ROOT / relative_path
        if not path.is_file():
            errors.append(f"Manifest output missing: {relative_path}")
            continue
        if path.stat().st_size != int(entry.get("size_bytes", -1)):
            errors.append(f"Size mismatch: {relative_path}")
        if sha256(path) != entry.get("sha256"):
            errors.append(f"SHA-256 mismatch: {relative_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, nargs="?", default=DEFAULT_DATASET)
    args = parser.parse_args()
    errors = validate(args.directory.resolve())
    if errors:
        print("ENHANCED PROVISIONAL TRAINING DATASET INVALID")
        for error in errors:
            print(f"  - {error}")
        return 1
    manifest = json.loads((args.directory / "manifest.json").read_text(encoding="utf-8"))
    counts = {split: manifest["splits"][split]["patch_count"] for split in SPLITS}
    print(
        "Enhanced provisional training dataset valid: "
        f"{counts}, {manifest['eligible_tasks']} high-confidence tasks; not a gold benchmark."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
