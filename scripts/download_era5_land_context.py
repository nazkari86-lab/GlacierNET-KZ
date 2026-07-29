#!/usr/bin/env python3
"""Download a compact, reproducible ERA5-Land monthly context for the study AOI."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/climate/era5_land_2000_2025_monthly.nc"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if OUTPUT.exists() and not args.refresh:
        print(f"Already exists: {OUTPUT.relative_to(ROOT)}")
        return 0
    import cdsapi

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    request = {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": ["2m_temperature", "total_precipitation", "snow_depth"],
        "year": [str(year) for year in range(2000, 2026)],
        "month": [f"{month:02d}" for month in range(1, 13)],
        "time": ["00:00"],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [44.1, 75.5, 42.4, 79.0],
    }
    client = cdsapi.Client()
    client.retrieve("reanalysis-era5-land-monthly-means", request).download(str(temporary))
    if not temporary.is_file() or temporary.stat().st_size < 1024:
        raise RuntimeError("CDS returned no usable ERA5-Land file")
    temporary.replace(OUTPUT)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    manifest = {
        "schema": "glaciernet-kz.era5-land-context.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "reanalysis-era5-land-monthly-means",
        "variables": request["variable"],
        "years": request["year"],
        "bbox_wgs84": [75.5, 42.4, 79.0, 44.1],
        "sha256": digest,
        "bytes": OUTPUT.stat().st_size,
        "scope": "Monthly climate context only; not local weather observations or event attribution.",
    }
    (OUTPUT.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
