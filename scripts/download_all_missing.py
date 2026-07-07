#!/usr/bin/env python3
"""Download all missing project data: Drive GeoTIFFs, WGMS FoG, GEE exports."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, data_loader  # noqa: E402

DRIVE_LIST = ROOT / "drive_file_list.json"
WGMS_ZIP = config.PROJECT_ROOT / "data" / "wgms" / "raw" / "DOI-WGMS-FoG-2026-02-10.zip"
WGMS_URL = "https://doi.org/10.5904/wgms-fog-2026-02-10"
LOG = config.PROJECT_ROOT / "logs" / "download_all.log"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def missing_satellite_files() -> list[dict]:
    """Return Drive file entries not yet on disk (skip *_subset* duplicates)."""
    entries = json.loads(DRIVE_LIST.read_text(encoding="utf-8"))
    missing = []
    for entry in entries:
        name = entry["name"]
        if "subset" in name:
            continue
        out_dir = config.DATA_RAW_SENTINEL2 if name.startswith("sentinel2") else config.DATA_RAW_LANDSAT
        out_path = out_dir / name
        expected = int(entry.get("size", 0))
        if out_path.exists() and out_path.stat().st_size == expected:
            continue
        missing.append(entry)
    return missing


def download_from_drive() -> None:
    missing = missing_satellite_files()
    if not missing:
        log("All Drive GeoTIFFs already present.")
        return
    total_mb = sum(int(f.get("size", 0)) for f in missing) / 1e6
    log(f"Downloading {len(missing)} GeoTIFFs from Google Drive (~{total_mb:.0f} MB)...")
    rc = subprocess.run(
        [sys.executable, str(ROOT / "download_drive.py")],
        cwd=str(ROOT),
    )
    if rc.returncode != 0:
        log(f"WARNING: download_drive.py exited with code {rc.returncode}")


def export_missing_via_gee() -> None:
    """Start GEE Drive exports for years not in drive_file_list.json."""
    import ee

    ee.Initialize(project="angular-operand-468315-k4")
    aoi = ee.Geometry.Rectangle(list(config.STUDY_AREA_BBOX))

    on_drive = {e["name"] for e in json.loads(DRIVE_LIST.read_text())}

    for year in config.YEARS_SENTINEL2:
        fname = f"sentinel2_{year}.tif"
        local = config.DATA_RAW_SENTINEL2 / fname
        if fname in on_drive or local.exists():
            continue
        log(f"GEE export → Drive: {fname}")
        img = data_loader.get_sentinel2(year, aoi)
        if img is None:
            log(f"  SKIP {year}: no Sentinel-2 scenes")
            continue
        data_loader.export_year_to_drive(img, year, aoi, prefix="sentinel2")

    for year in config.YEARS_LANDSAT:
        fname = f"landsat_{year}.tif"
        local = config.DATA_RAW_LANDSAT / fname
        if fname in on_drive or local.exists():
            continue
        log(f"GEE export → Drive: {fname}")
        img = data_loader.get_landsat(year, aoi)
        if img is None:
            log(f"  SKIP {year}: no Landsat scenes")
            continue
        img = data_loader.add_indices(img)
        data_loader.export_year_to_drive(img, year, aoi, prefix="landsat")

    log("GEE export tasks submitted. Check https://code.earthengine.google.com/tasks")
    log("Re-run this script after tasks complete to download new files from Drive.")


def download_wgms_fog() -> None:
    """Download full WGMS FoG archive if local zip is incomplete."""
    extract_dir = WGMS_ZIP.parent / "fog_extracted"
    state_csv = extract_dir / "data" / "state.csv"
    if state_csv.exists() and state_csv.stat().st_size > 1_000_000:
        log(f"WGMS FoG already extracted ({state_csv.stat().st_size / 1e6:.1f} MB state.csv)")
        return

    log(f"Downloading WGMS FoG from {WGMS_URL} ...")
    WGMS_ZIP.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(
        ["curl", "-L", "-o", str(WGMS_ZIP), WGMS_URL, "--progress-bar"],
        cwd=str(ROOT),
    )
    if rc.returncode != 0:
        log("WARNING: WGMS FoG download failed")
        return

    size_mb = WGMS_ZIP.stat().st_size / 1e6
    log(f"WGMS zip downloaded ({size_mb:.0f} MB), extracting...")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(WGMS_ZIP, "r") as zf:
        zf.extractall(extract_dir)
    log("WGMS FoG extracted.")

    fog_csv = extract_dir / "data" / "state.csv"
    if fog_csv.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "wgms_setup.py"), "--fog-csv", str(fog_csv)],
            cwd=str(ROOT),
            check=False,
        )


def verify_rgi() -> None:
    shp = config.DATA_RGI / "rgi_study_area.shp"
    if shp.exists():
        log(f"RGI shapefile OK: {shp.name} ({shp.stat().st_size / 1e6:.1f} MB)")
        return
    central = config.DATA_RGI / "RGI2000-v7.0-G-13_central_asia.shp"
    if central.exists():
        log("RGI central_asia present; clip to study area in notebook 02 if needed.")
        return
    log("WARNING: RGI shapefiles missing — download from https://www.glims.org/RGI/rgi70_dl.html")


def main() -> None:
    log("=" * 60)
    log("GlacierNET-KZ — download all missing data")
    log("=" * 60)

    verify_rgi()
    download_wgms_fog()
    download_from_drive()
    export_missing_via_gee()

    missing = missing_satellite_files()
    if missing:
        log(f"Still missing {len(missing)} GeoTIFFs (GEE exports may be pending):")
        for f in missing:
            log(f"  - {f['name']}")
    else:
        log("All satellite GeoTIFFs downloaded.")

    subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline_status.py")], cwd=str(ROOT))
    log("Done.")


if __name__ == "__main__":
    main()
