#!/usr/bin/env python3
"""Fetch an attributed, local OSM critical-asset extract for Risk Twin maps.

The output is a public-asset planning layer only. It is never a downstream
exposure, flood-route, population, or service-disruption layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/impact_assets"
ENDPOINTS = ("https://overpass.kumi.systems/api/interpreter", "https://overpass-api.de/api/interpreter")
QUERY = """[out:json][timeout:90];(
node[\"place\"~\"^(city|town|village)$\"](42.4,75.5,44.1,79.0);
node[\"amenity\"~\"^(school|hospital|clinic)$\"](42.4,75.5,44.1,79.0);
way[\"highway\"~\"^(primary|secondary)$\"](42.4,75.5,44.1,79.0);
);out center tags;"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    destination = OUT / "osm_critical_assets.geojson"
    if destination.exists() and not args.refresh:
        print(f"Already exists: {destination.relative_to(ROOT)} (use --refresh to replace)")
        return 0
    import requests

    payload = None
    failures: list[str] = []
    for endpoint in ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": QUERY},
                headers={"User-Agent": "GlacierNET-KZ/1.0 research evidence fetch"},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as error:
            failures.append(f"{endpoint}: {type(error).__name__}")
    if payload is None:
        raise RuntimeError("OSM extract unavailable; no local asset layer was created: " + "; ".join(failures))
    features = []
    for item in payload.get("elements", []):
        tags = item.get("tags", {})
        latitude, longitude = (
            item.get("lat") or item.get("center", {}).get("lat"),
            item.get("lon") or item.get("center", {}).get("lon"),
        )
        if latitude is None or longitude is None:
            continue
        asset_type = (
            "settlement" if "place" in tags else tags.get("amenity") or tags.get("highway") or "other_public_asset"
        )
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "asset_type": asset_type,
                    "name": tags.get("name"),
                    "source": "OpenStreetMap",
                    "source_id": f"{item.get('type')}/{item.get('id')}",
                },
                "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
            }
        )
    if not features:
        raise RuntimeError("OSM response contained no usable public assets; no local asset layer was created")
    OUT.mkdir(parents=True, exist_ok=True)
    document = {"type": "FeatureCollection", "features": features}
    destination.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "glaciernet-kz.osm-critical-assets.v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "OpenStreetMap via Overpass API",
                "licence": "ODbL; retain OpenStreetMap attribution",
                "bbox": [75.5, 42.4, 79.0, 44.1],
                "sha256": digest,
                "feature_count": len(features),
                "scope": "public-asset planning context only; not exposure or impact truth",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(features)} attributed OSM public assets to {destination.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
