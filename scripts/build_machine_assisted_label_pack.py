#!/usr/bin/env python3
"""Build a reproducible *provisional* label pack from RGI geometries.

The output is deliberately unsuitable for a gold-accuracy claim.  It is a
useful technical starting point for map QA, annotation tasks and reproducible
model diagnostics while independent human labels are unavailable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_provisional_glacier_cohort import select_stratified_glaciers  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rgi", type=Path, default=ROOT / "data/rgi/rgi_study_area.shp")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks/v2/annotations/machine_assisted")
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024])
    parser.add_argument("--per-area-class", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260727)
    args = parser.parse_args()

    import geopandas as gpd

    if args.per_area_class < 1:
        parser.error("--per-area-class must be positive")
    if not args.rgi.is_file():
        raise FileNotFoundError(args.rgi)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    inventory = gpd.read_file(args.rgi)
    selected = select_stratified_glaciers(inventory, per_class=args.per_area_class, seed=args.seed)
    selected = selected[["rgi_id", "area_km2", "area_class", "geometry"]].sort_values("rgi_id").reset_index(drop=True)

    rows: list[dict[str, object]] = []
    label_records: list[dict[str, object]] = []
    for year in sorted(set(args.years)):
        label_path = output / f"rgi_inventory_provisional_{year}.gpkg"
        if label_path.exists():
            label_path.unlink()
        labelled = selected.copy()
        labelled["observation_year"] = year
        labelled["label_tier"] = "machine_assisted_rgi_inventory"
        labelled["annotation_status"] = "provisional_not_gold"
        labelled["human_review_status"] = "not_reviewed"
        labelled.to_file(label_path, layer="glacier_labels", driver="GPKG")
        digest = sha256(label_path)
        label_records.append(
            {
                "year": year,
                "path": str(label_path.relative_to(ROOT)),
                "sha256": digest,
                "feature_count": int(len(labelled)),
                "source": "RGI 7.0 inventory geometry; copied without human redraw",
            }
        )
        for _, glacier in labelled.iterrows():
            rows.append(
                {
                    "glacier_id": glacier["rgi_id"],
                    "year": year,
                    "area_class": glacier["area_class"],
                    "rgi_area_km2": f"{float(glacier['area_km2']):.6f}",
                    "label_path": str(label_path.relative_to(ROOT)),
                    "label_sha256": digest,
                    "label_tier": "machine_assisted_rgi_inventory",
                    "annotation_status": "provisional_not_gold",
                    "human_review_status": "not_reviewed",
                    "claim_eligibility": "not_eligible_for_gold_accuracy_or_external_validation",
                }
            )

    queue_path = output / "machine_assisted_annotation_queue.csv"
    with queue_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "schema": "glaciernet-kz.machine-assisted-label-pack.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Technical QA and annotation bootstrap only",
        "prohibited_claims": [
            "independent expert gold-label accuracy",
            "independent external generalisation",
            "operational GLOF probability calibration",
            "validated historical trend or forecast",
        ],
        "source_inventory": {
            "path": str(args.rgi.resolve().relative_to(ROOT)),
            "sha256": sha256(args.rgi.resolve()),
            "licence_note": "Retain upstream RGI attribution and licence when distributing derived labels.",
        },
        "selection": {
            "method": "deterministic RGI-area tercile stratification",
            "per_area_class": args.per_area_class,
            "seed": args.seed,
            "glacier_ids": selected["rgi_id"].tolist(),
        },
        "label_records": label_records,
        "queue": {"path": str(queue_path.relative_to(ROOT)), "sha256": sha256(queue_path)},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(rows)} provisional label tasks for {len(selected)} glaciers; not gold labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
