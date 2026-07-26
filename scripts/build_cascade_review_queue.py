#!/usr/bin/env python3
"""Convert HMAGLOFDB records into a source-review queue, never into fake gold events."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/events/hmaglofdb/hmaglofdb_ile_alatau.gpkg"
OUTPUT = ROOT / "benchmarks/central_asia_cascade/tables/event_review_queue.csv"
MANIFEST = ROOT / "benchmarks/central_asia_cascade/manifests/event_review_queue.json"
FIELDS = (
    "event_id",
    "year",
    "month",
    "day",
    "date_precision",
    "lake_name",
    "glacier_name",
    "country",
    "longitude",
    "latitude",
    "scientific_reference",
    "other_reference",
    "source_review_status",
    "primary_source_verified",
    "eligible_for_strict_benchmark",
    "review_notes",
)


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def build_rows() -> list[dict[str, str]]:
    frame = gpd.read_file(SOURCE)
    rows: list[dict[str, str]] = []
    for _, record in frame.iterrows():
        year = clean(record.get("Year_exact")) or clean(record.get("Year_approx"))
        month = clean(record.get("Month"))
        day = clean(record.get("Day"))
        precision = "day" if day else "month" if month else "year"
        scientific = clean(record.get("Ref_scientific_full")) or clean(record.get("Ref_scientific"))
        rows.append(
            {
                "event_id": f"HMAGLOFDB-{int(record['GF_ID'])}",
                "year": year.removesuffix(".0"),
                "month": month.removesuffix(".0"),
                "day": day.removesuffix(".0"),
                "date_precision": precision,
                "lake_name": clean(record.get("Lake_name")),
                "glacier_name": clean(record.get("Glacier_name")),
                "country": clean(record.get("Country")),
                "longitude": clean(record.get("Lon_lake")),
                "latitude": clean(record.get("Lat_lake")),
                "scientific_reference": scientific,
                "other_reference": clean(record.get("Ref_other")),
                "source_review_status": "database_cited_pending_primary_source_review",
                "primary_source_verified": "false",
                "eligible_for_strict_benchmark": "false",
                "review_notes": "",
            }
        )
    return rows


def main() -> int:
    rows = build_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "schema": "glaciernet-kz.cascade-review-queue.v1",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "records": len(rows),
        "strict_eligible_records": 0,
        "non_event_controls": 0,
        "status": "source_review_required",
        "warning": "Database inclusion is not primary-source verification; absence is not a non-event control.",
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} pending event reviews; zero strict events or controls claimed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
