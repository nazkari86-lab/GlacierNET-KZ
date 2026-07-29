#!/usr/bin/env python3
"""Report whether strict scientific claims have their required external inputs.

This report is intentionally non-promotional: existence of files means that
automated processing can start, not that a scientific claim is validated.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/external/real_inputs"
DEFAULT_OUTPUT = ROOT / "benchmarks/v2/readiness/evidence_readiness.json"


def nonempty_csv(path: Path, required: set[str]) -> tuple[bool, str]:
    if not path.is_file():
        return False, "file missing"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        if not required <= columns:
            return False, f"missing columns: {', '.join(sorted(required - columns))}"
        if not any(True for _ in reader):
            return False, "no records"
    return True, "structurally ready; scientific review still required"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    base = args.input_dir.resolve()
    boundary = (
        next((p for p in (base / "zhetysu").glob("boundary.*") if p.suffix in {".geojson", ".gpkg", ".shp"}), None)
        if (base / "zhetysu").is_dir()
        else None
    )
    labels_ok, labels_note = nonempty_csv(
        base / "gold_labels" / "metadata.csv",
        {"glacier_id", "year", "annotator_id", "label_path", "label_sha256", "adjudication_status"},
    )
    events_ok, events_note = nonempty_csv(
        base / "events" / "source_review.csv",
        {"event_id", "event_outcome", "latitude", "longitude", "primary_source", "source_review_status"},
    )
    trend_ok, trend_note = nonempty_csv(
        base / "trend" / "reference_area.csv", {"year", "area_km2", "source", "method", "uncertainty_km2"}
    )
    claims = [
        {
            "id": "C4",
            "claim": "Independent expert gold-label accuracy",
            "automated_input_ready": labels_ok,
            "status": labels_note,
        },
        {
            "id": "C5",
            "claim": "Independent Zhetysu Alatau generalisation",
            "automated_input_ready": boundary is not None and labels_ok,
            "status": "boundary and labels ready for pipeline"
            if boundary and labels_ok
            else "needs authoritative boundary and adjudicated external labels",
        },
        {
            "id": "C6",
            "claim": "Operational GLOF warning or calibrated event probability",
            "automated_input_ready": events_ok,
            "status": events_note,
        },
        {
            "id": "C7",
            "claim": "Validated 2000-2020 glacier-loss trend or 2050 area forecast",
            "automated_input_ready": trend_ok,
            "status": trend_note,
        },
    ]
    report = {
        "schema": "glaciernet-kz.evidence-readiness.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(base.relative_to(ROOT)) if base.is_relative_to(ROOT) else str(base),
        "claims": claims,
        "provisional_machine_assisted_labels": "Not accepted as gold labels by this report.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for claim in claims:
        print(
            f"{claim['id']}: {'READY_FOR_AUTOMATION' if claim['automated_input_ready'] else 'BLOCKED'} — {claim['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
