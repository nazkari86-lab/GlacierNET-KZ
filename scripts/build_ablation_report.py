#!/usr/bin/env python3
"""Build a fail-closed same-patch feature ablation report."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ("dice_coefficient", "binary_io_u", "precision", "recall")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def validate_pair(control: dict, candidate: dict) -> None:
    for key in ("train_years", "validation_years", "test_years"):
        if control.get(key) != candidate.get(key):
            raise ValueError(f"Ablation split mismatch for {key}")
    control_shape = control.get("test_patch_shape", [])
    candidate_shape = candidate.get("test_patch_shape", [])
    if control_shape[:-1] != candidate_shape[:-1]:
        raise ValueError("Ablation test sample count or spatial shape differs")
    control_schema = control.get("feature_schema", [])
    candidate_schema = candidate.get("feature_schema", [])
    if candidate_schema[: len(control_schema)] != control_schema:
        raise ValueError("Candidate features do not preserve the control feature prefix")
    if len(candidate_schema) <= len(control_schema):
        raise ValueError("Candidate must add at least one feature")
    for report in (control, candidate):
        for metric in METRICS:
            value = float(report.get("metrics", {}).get(metric, -1))
            if not 0 <= value <= 1:
                raise ValueError(f"Missing or invalid metric: {metric}")


def verify_same_patch_lineage(control: dict, candidate: dict) -> dict:
    control_holdout = ROOT / control["patches_dir"] / "manifest.json"
    candidate_holdout = ROOT / candidate["patches_dir"] / "manifest.json"
    control_manifest = load_json(control_holdout)
    candidate_manifest = load_json(candidate_holdout)
    control_source = ROOT / control_manifest["source_manifest"]
    candidate_source = ROOT / candidate_manifest["source_manifest"]
    control_source_manifest = load_json(control_source)
    projected_from = (ROOT / str(control_source_manifest.get("source_manifest", ""))).resolve()
    if projected_from != candidate_source.resolve():
        raise ValueError("Control dataset is not a projection of the candidate dataset")
    expected_projection = list(range(len(control.get("feature_schema", []))))
    if control_source_manifest.get("channel_projection") != expected_projection:
        raise ValueError("Control dataset is not the expected prefix-channel projection")
    years = sorted(set(control["train_years"] + control["validation_years"] + control["test_years"]))
    checked_labels = 0
    for year in years:
        control_dir = ROOT / str(next(item["output_dir"] for item in control_manifest["years"] if item["year"] == year))
        candidate_dir = ROOT / str(
            next(item["output_dir"] for item in candidate_manifest["years"] if item["year"] == year)
        )
        for split in ("train", "val", "test"):
            control_label = control_dir / f"y_{split}.npy"
            candidate_label = candidate_dir / f"y_{split}.npy"
            if control_label.stat().st_ino != candidate_label.stat().st_ino:
                if file_sha256(control_label) != file_sha256(candidate_label):
                    raise ValueError(f"Label mismatch for {year}/{split}")
            checked_labels += 1
    return {
        "control_holdout_manifest_sha256": file_sha256(control_holdout),
        "candidate_holdout_manifest_sha256": file_sha256(candidate_holdout),
        "candidate_source_manifest_sha256": file_sha256(candidate_source),
        "same_patch_lineage": True,
        "label_arrays_verified": checked_labels,
    }


def build_report(control_path: Path, candidate_path: Path) -> dict:
    control = load_json(control_path)
    candidate = load_json(candidate_path)
    validate_pair(control, candidate)
    lineage = verify_same_patch_lineage(control, candidate)
    delta = {metric: float(candidate["metrics"][metric]) - float(control["metrics"][metric]) for metric in METRICS}
    dice_delta = delta["dice_coefficient"]
    if dice_delta > 0:
        finding = "Added Sentinel-1 channels improved Dice in this compact same-patch temporal ablation."
    elif dice_delta < 0:
        finding = "Added Sentinel-1 channels reduced Dice in this compact same-patch temporal ablation."
    else:
        finding = "Added Sentinel-1 channels did not change Dice in this compact same-patch temporal ablation."
    return {
        "schema": "glaciernet-kz.controlled-ablation.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comparison": "Sentinel-2 plus terrain versus Sentinel-2 plus terrain plus Sentinel-1 VV/VH",
        "protocol": "same sampled patches, identical labels and temporal splits, identical training configuration",
        "scope": "compact one-AOI temporal ablation with silver RGI-derived labels",
        "claims_allowed": ["same-patch feature ablation result"],
        "claims_not_allowed": [
            "cross-region generalisation",
            "independent expert-label accuracy",
            "operational superiority",
            "replacement of the full benchmark",
        ],
        "control_report": relative(control_path),
        "candidate_report": relative(candidate_path),
        "control_report_sha256": file_sha256(control_path),
        "candidate_report_sha256": file_sha256(candidate_path),
        "control_feature_schema": control["feature_schema"],
        "candidate_feature_schema": candidate["feature_schema"],
        "added_features": candidate["feature_schema"][len(control["feature_schema"]) :],
        "train_years": control["train_years"],
        "validation_years": control["validation_years"],
        "test_years": control["test_years"],
        "test_samples": control["test_patch_shape"][0],
        "metrics": {
            "control": {metric: float(control["metrics"][metric]) for metric in METRICS},
            "candidate": {metric: float(candidate["metrics"][metric]) for metric in METRICS},
            "candidate_minus_control": delta,
        },
        "finding": finding,
        "lineage": lineage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_report(args.control.resolve(), args.candidate.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
