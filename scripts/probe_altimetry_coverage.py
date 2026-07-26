#!/usr/bin/env python3
"""Probe NASA CMR for candidate SWOT and ICESat-2 coverage without downloading data."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import earthaccess


ROOT = Path(__file__).resolve().parents[1]
BBOX = (75.5, 42.2, 78.2, 43.8)
START = "2024-01-01"


def temporal(granule: dict) -> dict:
    return granule.get("umm", {}).get("TemporalExtent", {}).get("RangeDateTime", {})


def probe(short_name: str, version: str, count: int = 5000) -> dict:
    granules = earthaccess.search_data(
        short_name=short_name,
        version=version,
        bounding_box=BBOX,
        temporal=(START, date.today().isoformat()),
        count=count,
    )
    sizes = [float(item.size() or 0) for item in granules]
    starts = [temporal(item).get("BeginningDateTime") for item in granules]
    starts = sorted(value for value in starts if value)
    return {
        "short_name": short_name,
        "version": version,
        "candidate_granules": len(granules),
        "candidate_size_mb": round(sum(sizes), 3),
        "first_candidate_time": starts[0] if starts else None,
        "last_candidate_time": starts[-1] if starts else None,
        "sample_urls": [url for item in granules[:3] for url in item.data_links()[:1]],
        "interpretation": (
            "CMR spatial intersection is a candidate filter. Granule-internal lake/track "
            "coordinates must still be filtered before claiming observations in the AOI."
        ),
    }


if __name__ == "__main__":
    earthaccess.login(strategy="netrc")
    result = {
        "query_date": date.today().isoformat(),
        "aoi_bbox_epsg4326": list(BBOX),
        "temporal_start": START,
        "datasets": [
            probe("SWOT_L2_HR_LakeSP_2.0", "2.0"),
            probe("ATL13", "007"),
        ],
        "download_policy": "Metadata-only probe; no granules downloaded.",
    }
    output = ROOT / "data/online_coverage/nasa_altimetry_candidates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
