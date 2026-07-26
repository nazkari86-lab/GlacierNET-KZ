#!/usr/bin/env python3
"""Validate a controlled ablation report and all referenced evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ("dice_coefficient", "binary_io_u", "precision", "recall")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.report.read_text(encoding="utf-8"))
    errors: list[str] = []
    if payload.get("schema") != "glaciernet-kz.controlled-ablation.v1":
        errors.append("unsupported ablation schema")
    for name in ("control", "candidate"):
        path = ROOT / str(payload.get(f"{name}_report", ""))
        if not path.is_file():
            errors.append(f"missing {name} report: {path}")
        elif sha256(path) != payload.get(f"{name}_report_sha256"):
            errors.append(f"{name} report SHA-256 mismatch")
    if payload.get("added_features") != ["VV_dB_normalized", "VH_dB_normalized"]:
        errors.append("expected exactly Sentinel-1 VV/VH added features")
    if not payload.get("lineage", {}).get("same_patch_lineage"):
        errors.append("same-patch lineage is not verified")
    if int(payload.get("lineage", {}).get("label_arrays_verified", 0)) < 1:
        errors.append("no label arrays were verified")
    metrics = payload.get("metrics", {})
    for metric in METRICS:
        try:
            expected = float(metrics["candidate"][metric]) - float(metrics["control"][metric])
            actual = float(metrics["candidate_minus_control"][metric])
        except (KeyError, TypeError, ValueError):
            errors.append(f"missing metric evidence: {metric}")
            continue
        if abs(expected - actual) > 1e-12:
            errors.append(f"incorrect delta: {metric}")
    if not payload.get("claims_not_allowed"):
        errors.append("claims_not_allowed must be explicit")
    if errors:
        print("ABLATION REPORT VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Ablation report validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
