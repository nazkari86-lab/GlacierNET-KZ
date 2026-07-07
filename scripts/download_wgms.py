#!/usr/bin/env python3
"""Download and extract WGMS Fluctuations of Glaciers (FoG) database.

Source: https://doi.org/10.5904/wgms-fog-2026-02-10 (~868 MB zip)

Usage:
    python scripts/download_wgms.py
    python scripts/download_wgms.py --extract-only
    python scripts/download_wgms.py --fog-csv data/wgms/raw/fog_extracted/measurements.csv
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "wgms" / "raw"
EXTRACT_DIR = RAW_DIR / "fog_extracted"
ZIP_URL = "https://wgms.ch/downloads/DOI-WGMS-FoG-2026-02-10.zip"
ZIP_PATH = RAW_DIR / "DOI-WGMS-FoG-2026-02-10.zip"
MIN_ZIP_BYTES = 30_000_000  # ~37 MB compressed (868 MB is uncompressed CSV total)


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= MIN_ZIP_BYTES:
        print(f"Already downloaded: {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
        return

    if dest.exists():
        dest.unlink()

    print(f"Downloading {url}")
    print(f"  → {dest}")
    cmd = ["curl", "-L", "--fail", "--retry", "5", "--retry-delay", "3", "-o", str(dest), url]
    subprocess.run(cmd, check=True)

    size = dest.stat().st_size
    print(f"Downloaded {size / 1e6:.1f} MB")
    if size < MIN_ZIP_BYTES:
        raise RuntimeError(
            f"Download too small ({size} bytes). Expected ~868 MB. "
            "Check network or download manually from https://wgms.ch/data_databaseversions/"
        )


def extract(zip_path: Path, dest: Path) -> None:
    if not zipfile.is_zipfile(zip_path):
        raise RuntimeError(f"Not a valid zip: {zip_path}")

    # FoG change.csv is ~815 MB uncompressed — extract only files needed for area validation
    selective = ["data/state.csv", "data/glacier.csv"]

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    print(f"Extracting {selective} from {zip_path.name} → {dest}")
    with zipfile.ZipFile(zip_path) as zf:
        for name in selective:
            zf.extract(name, dest)
    csv_files = list(dest.rglob("*.csv"))
    print(f"Extracted {len(csv_files)} CSV files")


def find_area_csv(extract_dir: Path) -> Path | None:
    """Prefer WGMS FoG state.csv for glacier area time series."""
    state = extract_dir / "data" / "state.csv"
    if state.is_file():
        return state
    candidates = list(extract_dir.rglob("*.csv"))
    area_csvs = [p for p in candidates if "state" in p.name.lower() or "area" in p.name.lower()]
    pool = area_csvs or candidates
    if not pool:
        return None
    return max(pool, key=lambda p: p.stat().st_size)


def run_wgms_setup(fog_csv: Path) -> None:
    setup = ROOT / "scripts" / "wgms_setup.py"
    subprocess.run([sys.executable, str(setup), "--fog-csv", str(fog_csv)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download WGMS FoG database for Tuyuksu validation")
    parser.add_argument("--extract-only", action="store_true", help="Skip download, only extract existing zip")
    parser.add_argument("--fog-csv", type=Path, help="Run wgms_setup.py on this CSV after extract")
    parser.add_argument("--skip-setup", action="store_true", help="Do not run wgms_setup.py")
    args = parser.parse_args()

    if not args.extract_only:
        download(ZIP_URL, ZIP_PATH)

    if not ZIP_PATH.exists():
        print(f"Zip not found: {ZIP_PATH}", file=sys.stderr)
        sys.exit(1)

    extract(ZIP_PATH, EXTRACT_DIR)

    fog_csv = args.fog_csv or find_area_csv(EXTRACT_DIR)
    if fog_csv and not args.skip_setup:
        print(f"Running wgms_setup on {fog_csv}")
        run_wgms_setup(fog_csv)
    elif fog_csv:
        print(f"FoG CSV found: {fog_csv}")
    else:
        print("No CSV found in archive — run wgms_setup.py manually")


if __name__ == "__main__":
    main()
