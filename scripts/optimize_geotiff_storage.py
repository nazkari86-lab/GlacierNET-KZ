#!/usr/bin/env python3
"""Losslessly recompress large GeoTIFFs and retain an auditable report.

The source file is replaced atomically only when GDAL confirms identical
dimensions, georeferencing, band semantics, nodata values, and per-band pixel
checksums. A smaller output is also required. This keeps scientific values
unchanged while reducing both local and object-storage size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "benchmarks" / "central_asia_cascade" / "manifests" / "storage_optimization.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gdal_info(path: Path, *, checksum: bool = False) -> dict[str, Any]:
    command = ["gdalinfo", "-json"]
    if checksum:
        command.append("-checksum")
    command.append(str(path))
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def semantic_signature(info: dict[str, Any]) -> dict[str, Any]:
    bands = []
    for band in info.get("bands", []):
        bands.append(
            {
                "band": band.get("band"),
                "type": band.get("type"),
                "colorInterpretation": band.get("colorInterpretation"),
                "description": band.get("description"),
                "noDataValue": band.get("noDataValue"),
                "offset": band.get("offset"),
                "scale": band.get("scale"),
                "unit": band.get("unit"),
                "checksum": band.get("checksum"),
                "metadata": band.get("metadata", {}),
                "mask": band.get("mask"),
                "overviews": [
                    {"size": item.get("size"), "checksum": item.get("checksum")} for item in band.get("overviews", [])
                ],
            }
        )
    return {
        "size": info.get("size"),
        "coordinateSystem": info.get("coordinateSystem", {}).get("wkt"),
        "geoTransform": info.get("geoTransform"),
        "gcps": info.get("gcps"),
        "metadata": {key: value for key, value in info.get("metadata", {}).items() if key != "IMAGE_STRUCTURE"},
        "bands": bands,
    }


def creation_options(info: dict[str, Any]) -> list[str]:
    band_types = {str(item.get("type", "")) for item in info.get("bands", [])}
    predictor = "3" if any("Float" in item for item in band_types) else "2"
    values = {
        "TILED": "YES",
        "BLOCKXSIZE": "512",
        "BLOCKYSIZE": "512",
        "COMPRESS": "ZSTD",
        "ZSTD_LEVEL": "9",
        "PREDICTOR": predictor,
        "BIGTIFF": "IF_SAFER",
        "NUM_THREADS": "ALL_CPUS",
        "COPY_SRC_OVERVIEWS": "YES",
    }
    return [part for key, value in values.items() for part in ("-co", f"{key}={value}")]


def load_report(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema": "glaciernet-kz.storage-optimization.v1",
        "method": "lossless GeoTIFF ZSTD level 9 with atomic pixel-checksum gate",
        "files": [],
    }


def save_report(path: Path, report: dict[str, Any]) -> None:
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    report["totals"] = {
        "files_optimized": len(report["files"]),
        "original_bytes": sum(item["original_bytes"] for item in report["files"]),
        "optimized_bytes": sum(item["optimized_bytes"] for item in report["files"]),
    }
    report["totals"]["saved_bytes"] = report["totals"]["original_bytes"] - report["totals"]["optimized_bytes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def optimize(path: Path, report: dict[str, Any], report_path: Path) -> str:
    relative = str(path.relative_to(ROOT))
    existing = next((item for item in report["files"] if item["path"] == relative), None)
    if existing:
        current = gdal_info(path)
        image_structure = current.get("metadata", {}).get("IMAGE_STRUCTURE", {})
        if (
            image_structure.get("COMPRESSION") == "ZSTD"
            and image_structure.get("PREDICTOR") in {"2", "3"}
            and sha256(path) == existing.get("optimized_sha256")
        ):
            return "verified_optimized"
        report["files"].remove(existing)
        save_report(report_path, report)

    initial = gdal_info(path)
    image_structure = initial.get("metadata", {}).get("IMAGE_STRUCTURE", {})
    if image_structure.get("COMPRESSION") == "ZSTD" and image_structure.get("PREDICTOR") in {"2", "3"}:
        return "already_optimized"

    original_bytes = path.stat().st_size
    free_bytes = shutil.disk_usage(path.parent).free
    if free_bytes < min(original_bytes + 256 * 1024 * 1024, 2 * 1024**3):
        raise RuntimeError(f"Insufficient temporary space for {relative}: {free_bytes} bytes free")

    temporary = path.with_name(path.name + ".storage-optimization.tmp.tif")
    if temporary.exists():
        temporary.unlink()
    original_hash = sha256(path)
    original_signature = semantic_signature(gdal_info(path, checksum=True))
    command = ["gdal_translate", "-q", *creation_options(initial), str(path), str(temporary)]
    try:
        subprocess.run(command, check=True)
        optimized_signature = semantic_signature(gdal_info(temporary, checksum=True))
        if optimized_signature != original_signature:
            raise RuntimeError(f"Scientific equivalence gate failed for {relative}")
        optimized_bytes = temporary.stat().st_size
        if optimized_bytes >= original_bytes:
            temporary.unlink()
            return "not_smaller"
        optimized_hash = sha256(temporary)
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    report["files"].append(
        {
            "path": relative,
            "original_bytes": original_bytes,
            "optimized_bytes": optimized_bytes,
            "saved_bytes": original_bytes - optimized_bytes,
            "saved_percent": round((1 - optimized_bytes / original_bytes) * 100, 3),
            "original_sha256": original_hash,
            "optimized_sha256": optimized_hash,
            "pixel_checksums": [item["checksum"] for item in original_signature["bands"]],
            "compression": "ZSTD",
            "predictor": "3" if any("Float" in str(item["type"]) for item in original_signature["bands"]) else "2",
        }
    )
    save_report(report_path, report)
    return "optimized"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=["data/raw"])
    parser.add_argument("--min-size-mib", type=float, default=50)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report = load_report(report_path)
    minimum = int(args.min_size_mib * 1024 * 1024)
    candidates: list[Path] = []
    for raw in args.paths:
        target = Path(raw)
        target = target if target.is_absolute() else ROOT / target
        if target.is_file():
            candidates.append(target)
        elif target.is_dir():
            candidates.extend(sorted(target.rglob("*.tif")))
    candidates = [item for item in candidates if item.is_file() and item.stat().st_size >= minimum]
    for index, path in enumerate(candidates, start=1):
        before = path.stat().st_size
        result = optimize(path, report, report_path)
        after = path.stat().st_size
        print(f"[{index}/{len(candidates)}] {path.relative_to(ROOT)}: {result} ({before} -> {after})", flush=True)
    save_report(report_path, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
