#!/usr/bin/env python3
"""Download a local JRC Global Surface Water context raster via Earth Engine."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/water/jrc_gsw_context_100m.tif"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if OUT.exists() and not args.refresh:
        print(f"Already exists: {OUT.relative_to(ROOT)}")
        return 0
    import ee
    import rasterio
    import requests

    ee.Initialize()
    bbox = [75.5, 42.4, 79.0, 44.1]
    region = ee.Geometry.Rectangle(bbox)
    image = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select(["occurrence", "seasonality", "recurrence"])
        .clip(region)
        .toByte()
    )
    url = image.getDownloadURL(
        {
            "name": "jrc_gsw_context_100m",
            "scale": 100,
            "crs": "EPSG:4326",
            "region": region.getInfo()["coordinates"],
            "format": "GEO_TIFF",
            "filePerBand": False,
        }
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".tif.part")
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)
    with rasterio.open(temporary) as dataset:
        if dataset.count != 3 or dataset.crs is None:
            raise RuntimeError("JRC export is not a three-band georeferenced raster")
        metadata = {
            "bands": dataset.count,
            "crs": dataset.crs.to_string(),
            "width": dataset.width,
            "height": dataset.height,
            "resolution": list(dataset.res),
        }
    temporary.replace(OUT)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    (OUT.parent / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "glaciernet-kz.jrc-water-context.v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "JRC/GSW1_4/GlobalSurfaceWater",
                "bbox_wgs84": bbox,
                "bands": ["occurrence", "seasonality", "recurrence"],
                "scope": "Independent surface-water context; not lake bathymetry, discharge or event probability.",
                "sha256": digest,
                "bytes": OUT.stat().st_size,
                "raster": metadata,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Downloaded {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
