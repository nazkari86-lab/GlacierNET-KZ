#!/usr/bin/env python3
"""Resumable, checksum-aware data sync for CentralAsia-GlacierBench.

The default compact profile fits the current workstation.  Large Cryo-Bench
archives require an explicit flag and a free-space check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data/external/centralasia_glacierbench"

COMPACT_DOWNLOADS = (
    {
        "id": "hma_ltg",
        "url": "https://zenodo.org/api/records/17369580/files/HMA_LTG.gpkg/content",
        "path": DATA_ROOT / "hma_ltg/HMA_LTG.gpkg",
        "sha256": None,
        "expected_size": 30_208_000,
    },
    {
        "id": "glavitu_code",
        "url": "https://github.com/konstantin-a-maslov/scalable_glacier_mapping/archive/refs/tags/v1.0.tar.gz",
        "path": DATA_ROOT / "glavitu/scalable_glacier_mapping-v1.0.tar.gz",
        "sha256": None,
        "expected_size": 3_454_349,
    },
    {
        "id": "cryobench_gld",
        "url": "https://huggingface.co/datasets/Sk-21/Cryo-Bench/resolve/main/data/GLD.tar.gz?download=true",
        "path": DATA_ROOT / "cryobench/GLD.tar.gz",
        "sha256": "e1a0c16f04bb545643662d345d3fdab219872a785aa4429e9301428404e543d1",
        "expected_size": 1_025_438_850,
    },
    {
        "id": "oggm_rgi7_glacier_statistics",
        "url": (
            "https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L3-L5_files/"
            "2025.6/elev_bands/W5E5/regional_spinup/RGI70G/b_160/L5/summary/"
            "glacier_statistics_13.csv"
        ),
        "path": DATA_ROOT / "oggm/glacier_statistics_13.csv",
        "sha256": None,
        "expected_size": 69_466_100,
    },
    {
        "id": "oggm_rgi7_historical_run",
        "url": (
            "https://cluster.klima.uni-bremen.de/~oggm/gdirs/oggm_v1.6/L3-L5_files/"
            "2025.6/elev_bands/W5E5/regional_spinup/RGI70G/b_160/L5/summary/"
            "historical_run_output_13.nc"
        ),
        "path": DATA_ROOT / "oggm/historical_run_output_13.nc",
        "sha256": None,
        "expected_size": 16_798_565,
    },
    {
        "id": "hugonnet_geodetic_rates",
        "url": (
            "https://cluster.klima.uni-bremen.de/~oggm/geodetic_ref_mb/"
            "hugonnet_2021_ds_rgi60_pergla_rates_10_20_worldwide_filled.hdf"
        ),
        "path": DATA_ROOT / "hugonnet/hugonnet_2021_ds_rgi60_pergla_rates_10_20_worldwide_filled.hdf",
        "sha256": None,
        "expected_size": 40_254_724,
    },
)

LARGE_DOWNLOADS = (
    {
        "id": "cryobench_glid",
        "url": "https://huggingface.co/datasets/Sk-21/Cryo-Bench/resolve/main/data/GLID.tar.gz?download=true",
        "path": DATA_ROOT / "cryobench/GLID.tar.gz",
        "sha256": "6854bb969e51109f469ca0e659de7efb0e4363a42f67d8f699f02a29383e92a4",
        "size": 8_226_485_231,
    },
    {
        "id": "cryobench_gsdd",
        "url": "https://huggingface.co/datasets/Sk-21/Cryo-Bench/resolve/main/data/GSDD.tar.gz?download=true",
        "path": DATA_ROOT / "cryobench/GSDD.tar.gz",
        "sha256": "38e624369e0b20751386f8c8f5768257158c259fffa6b987cd150e65166288eb",
        "size": 15_040_647_837,
    },
)

GLAVITU_WEIGHTS = {
    "glavitu_global_weights.h5": "1HLIVlWuGfMx_jZQleHlQmuzvzHVMRTOd",
    "glavitu_finetuning_HMA_weights.h5": "1hNRFR55MtkQjSH4ZRBcfswPNXnhafQ6i",
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download(entry: dict[str, object]) -> dict[str, object]:
    path = Path(entry["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    expected = entry.get("sha256")
    expected_size = entry.get("expected_size")
    if path.is_file() and expected and digest(path) == expected:
        return {"id": entry["id"], "status": "verified_cached", "path": str(path.relative_to(ROOT))}
    if path.is_file() and expected_size and path.stat().st_size == int(expected_size):
        return {
            "id": entry["id"],
            "status": "verified_size_cached",
            "path": str(path.relative_to(ROOT)),
            "sha256": digest(path),
            "size_bytes": path.stat().st_size,
        }
    command = [
        "curl",
        "-fL",
        "--retry",
        "12",
        "--retry-all-errors",
        "-C",
        "-",
        "-o",
        str(path),
        str(entry["url"]),
    ]
    subprocess.run(command, check=True)
    actual = digest(path)
    if expected_size and path.stat().st_size != int(expected_size):
        raise RuntimeError(f"size mismatch for {entry['id']}: {path.stat().st_size} != {expected_size}")
    if expected and actual != expected:
        raise RuntimeError(f"checksum mismatch for {entry['id']}: {actual}")
    return {
        "id": entry["id"],
        "status": "verified" if expected else "downloaded_digest_computed",
        "path": str(path.relative_to(ROOT)),
        "sha256": actual,
        "size_bytes": path.stat().st_size,
    }


def download_glavitu_weights() -> list[dict[str, object]]:
    try:
        import gdown
    except ImportError as exc:
        raise RuntimeError("Install gdown>=5.2 to retrieve public GlaViTU weights") from exc
    output = DATA_ROOT / "glavitu/weights"
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for name, file_id in GLAVITU_WEIGHTS.items():
        target = output / name
        if not target.is_file():
            result = gdown.download(id=file_id, output=str(target), quiet=False, resume=True)
            if result is None:
                raise RuntimeError(f"GlaViTU weight download failed: {name}")
        rows.append(
            {
                "id": name,
                "status": "downloaded_digest_computed",
                "path": str(target.relative_to(ROOT)),
                "sha256": digest(target),
                "size_bytes": target.stat().st_size,
            }
        )
    return rows


def fetch_itslive_catalog() -> dict[str, object]:
    """Persist the real STAC response for cubes intersecting the study domain."""
    payload = json.dumps(
        {
            "collections": ["itslive-cubes"],
            "bbox": [74.0, 40.0, 82.0, 46.0],
            "limit": 100,
        }
    ).encode()
    request = urllib.request.Request(
        "https://stac.itslive.cloud/search",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "GlacierNET-KZ/0.2"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        catalog = json.load(response)
    features = catalog.get("features", [])
    if not features:
        raise RuntimeError("ITS_LIVE STAC returned no Central Asia cubes")
    target = DATA_ROOT / "itslive/stac_cubes.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    return {
        "id": "itslive_stac_catalog",
        "status": "metadata_only",
        "path": str(target.relative_to(ROOT)),
        "sha256": digest(target),
        "size_bytes": target.stat().st_size,
        "feature_count": len(features),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-large", action="store_true")
    parser.add_argument("--skip-weights", action="store_true")
    args = parser.parse_args()

    selected = list(COMPACT_DOWNLOADS)
    if args.include_large:
        required = sum(int(entry["size"]) for entry in LARGE_DOWNLOADS)
        free = shutil.disk_usage(DATA_ROOT.parent if DATA_ROOT.parent.exists() else ROOT).free
        if free < required + 5_000_000_000:
            raise RuntimeError(
                f"large profile needs at least {(required + 5e9) / 1e9:.1f} GB free; found {free / 1e9:.1f} GB"
            )
        selected.extend(LARGE_DOWNLOADS)

    rows = [download(entry) for entry in selected]
    rows.append(fetch_itslive_catalog())
    if not args.skip_weights:
        rows.extend(download_glavitu_weights())
    manifest = {
        "schema": "centralasia-glacierbench.sync.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": "large" if args.include_large else "compact",
        "artifacts": rows,
    }
    manifest_path = DATA_ROOT / "sync_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
