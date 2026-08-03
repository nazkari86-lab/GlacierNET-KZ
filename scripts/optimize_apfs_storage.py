#!/usr/bin/env python3
"""Apply transparent APFS compression without changing file bytes or paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "benchmarks" / "central_asia_cascade" / "manifests" / "apfs_storage_optimization.json"
SUPPORTED_SUFFIXES = {".npy", ".pkl", ".pickle", ".joblib", ".h5"}
AFSCTOOL = Path("/opt/homebrew/bin/afsctool")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def physical_bytes(path: Path) -> int:
    return path.stat().st_blocks * 512


def is_candidate(path: Path, minimum: int) -> bool:
    if not path.is_file() or path.stat().st_size < minimum:
        return False
    return path.suffix.lower() in SUPPORTED_SUFFIXES or ".data-" in path.name


def validate_npy(path: Path) -> dict[str, object] | None:
    if path.suffix.lower() != ".npy":
        return None
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    first = array.reshape(-1)[0].item() if array.size else None
    last = array.reshape(-1)[-1].item() if array.size else None
    return {"shape": list(array.shape), "dtype": str(array.dtype), "first": first, "last": last}


def is_apfs_compressed(path: Path) -> bool:
    result = subprocess.run([str(AFSCTOOL), "-v", str(path)], capture_output=True, text=True, check=False)
    return result.returncode == 0 and "File is HFS+/APFS compressed." in result.stdout


def load_previous_records() -> dict[str, dict[str, object]]:
    try:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if report.get("schema") != "glaciernet-kz.apfs-storage-optimization.v1":
        return {}
    files = report.get("files")
    if not isinstance(files, list):
        return {}
    return {str(item["path"]): item for item in files if isinstance(item, dict) and isinstance(item.get("path"), str)}


def save_report(records: list[dict[str, object]]) -> None:
    logical = sum(int(item["logical_bytes"]) for item in records)
    physical = sum(int(item["physical_bytes_after"]) for item in records)
    report = {
        "schema": "glaciernet-kz.apfs-storage-optimization.v1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "method": "transparent APFS compression; SHA-256 and mmap validation retained",
        "platform_scope": "local APFS physical storage only; object-storage size is unchanged",
        "totals": {
            "files_verified": len(records),
            "logical_bytes": logical,
            "physical_bytes_after": physical,
            "physical_bytes_saved_vs_logical": max(0, logical - physical),
        },
        "files": records,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, REPORT_PATH)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["data/processed", "models"])
    parser.add_argument("--min-size-mib", type=float, default=1)
    args = parser.parse_args()
    if not AFSCTOOL.is_file():
        raise RuntimeError("afsctool is required; install it with Homebrew")
    minimum = int(args.min_size_mib * 1024 * 1024)
    candidates: list[Path] = []
    for raw in args.paths:
        target = Path(raw)
        target = target if target.is_absolute() else ROOT / target
        if target.is_file() and is_candidate(target, minimum):
            candidates.append(target)
        elif target.is_dir():
            candidates.extend(item for item in target.rglob("*") if is_candidate(item, minimum))
    records: list[dict[str, object]] = []
    previous = load_previous_records()
    for index, path in enumerate(sorted(set(candidates)), start=1):
        relative = str(path.relative_to(ROOT))
        before_hash = sha256(path)
        npy_before = validate_npy(path)
        before_physical = physical_bytes(path)
        existing = previous.get(relative)
        if existing and existing.get("sha256") == before_hash and is_apfs_compressed(path):
            records.append(
                {
                    **existing,
                    "logical_bytes": path.stat().st_size,
                    "physical_bytes_before": before_physical,
                    "physical_bytes_after": before_physical,
                    "physical_bytes_saved_this_run": 0,
                    "npy": npy_before,
                }
            )
            save_report(records)
            print(f"[{index}/{len(candidates)}] {relative}: verified_compressed", flush=True)
            continue
        subprocess.run([str(AFSCTOOL), "-c", str(path)], check=True)
        after_hash = sha256(path)
        npy_after = validate_npy(path)
        if after_hash != before_hash or npy_after != npy_before:
            raise RuntimeError(f"Transparent compression validation failed for {relative}")
        after_physical = physical_bytes(path)
        records.append(
            {
                "path": relative,
                "sha256": after_hash,
                "logical_bytes": path.stat().st_size,
                "physical_bytes_before": before_physical,
                "physical_bytes_after": after_physical,
                "physical_bytes_saved_this_run": max(0, before_physical - after_physical),
                "npy": npy_after,
            }
        )
        save_report(records)
        print(
            f"[{index}/{len(candidates)}] {relative}: {before_physical} -> {after_physical} physical bytes",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
