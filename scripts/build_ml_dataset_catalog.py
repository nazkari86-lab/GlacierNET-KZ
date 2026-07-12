#!/usr/bin/env python3
"""Build a checksummed, machine-readable catalog of local ML training sources."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

OUT_JSON = config.RESULTS_DIR / "ml_dataset_catalog.json"
OUT_CSV = config.TABLES_DIR / "ml_dataset_catalog.csv"

DATASETS = (
    {
        "id": "sentinel2_sr",
        "role": "primary optical segmentation input",
        "access_mode": "local Earth Engine exports",
        "citation_url": "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED",
        "paths": lambda: sorted(config.DATA_RAW_SENTINEL2.glob("sentinel2_*.tif")),
    },
    {
        "id": "landsat_collection2",
        "role": "historical optical input",
        "access_mode": "local Earth Engine exports",
        "citation_url": "https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2",
        "paths": lambda: sorted(config.DATA_RAW_LANDSAT.glob("landsat_*.tif")),
    },
    {
        "id": "rgi_v7_central_asia",
        "role": "supervised glacier-outline labels",
        "access_mode": "local official archive",
        "citation_url": "https://www.glims.org/RGI/",
        "paths": lambda: sorted(config.DATA_RGI.glob("RGI2000-v7.0-G-13_central_asia.*")),
    },
    {
        "id": "wgms_fog_2026_02_10",
        "role": "area and change validation",
        "access_mode": "local official archive",
        "citation_url": "https://doi.org/10.5904/wgms-fog-2026-02-10",
        "paths": lambda: [ROOT / "data/wgms/raw/DOI-WGMS-FoG-2026-02-10.zip"],
    },
    {
        "id": "glathida_main",
        "role": "external thickness supervision and transfer-learning reference",
        "access_mode": "public WGMS GitLab archive",
        "citation_url": "https://gitlab.com/wgms/glathida",
        "paths": lambda: [ROOT / "data/external/glathida/glathida-main.tar.gz"],
    },
    {
        "id": "copernicus_dem_glo30",
        "role": "terrain features: elevation, slope, aspect",
        "access_mode": "public AWS Open Data",
        "citation_url": "https://registry.opendata.aws/copernicus-dem/",
        "paths": lambda: sorted((ROOT / "data/ancillary/copdem").glob("*.tif")),
    },
    {
        "id": "esa_worldcover_2021",
        "role": "land-cover context and hard-negative analysis",
        "access_mode": "public ESA S3",
        "citation_url": "https://esa-worldcover.org/",
        "paths": lambda: sorted((ROOT / "data/ancillary/worldcover").glob("ESA_WorldCover*.tif")),
    },
    {
        "id": "sentinel1_summer_composites",
        "role": "SAR features for cloud-robust multimodal segmentation",
        "access_mode": "Earth Engine export queue",
        "citation_url": "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD",
        "paths": lambda: sorted((ROOT / "data/ancillary/sentinel1").glob("*.tif")),
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, int | str]:
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def sentinel1_state(files: list[Path]) -> str:
    manifest_path = ROOT / "data/ancillary/sentinel1/export_manifest.json"
    if not manifest_path.exists():
        return "ready" if files else "not_local"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        entry["expected_filename"] for entry in manifest.get("entries", []) if entry.get("state") != "no_scenes"
    }
    local_names = {path.name for path in files}
    states = {entry.get("state") for entry in manifest.get("entries", [])}
    if expected and expected.issubset(local_names) and states == {"no_scenes", "downloaded"}:
        return "ready"
    if files:
        return "partial_download"
    return "export_submitted" if "submitted" in states else "not_local"


def build_catalog() -> list[dict]:
    rows: list[dict] = []
    for dataset in DATASETS:
        files = [path for path in dataset["paths"]() if path.is_file()]
        records = [file_record(path) for path in files]
        state = "ready" if records else "not_local"
        if dataset["id"] == "sentinel1_summer_composites":
            state = sentinel1_state(files)
        rows.append(
            {
                "id": dataset["id"],
                "role": dataset["role"],
                "access_mode": dataset["access_mode"],
                "citation_url": dataset["citation_url"],
                "state": state,
                "file_count": len(records),
                "total_bytes": sum(int(record["bytes"]) for record in records),
                "files": records,
            }
        )
    return rows


def main() -> int:
    rows = build_catalog()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(ROOT),
        "datasets": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "role", "access_mode", "state", "file_count", "total_bytes", "citation_url"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows([{key: row[key] for key in writer.fieldnames} for row in rows])
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_CSV}")
    for row in rows:
        print(f"{row['id']}: {row['state']} ({row['file_count']} files, {row['total_bytes'] / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
