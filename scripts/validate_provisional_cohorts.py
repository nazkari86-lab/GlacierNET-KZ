#!/usr/bin/env python3
"""Validate local provisional cohorts without allowing them to upgrade scientific claims."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/v2/provisional"


def validate() -> list[str]:
    errors: list[str] = []
    ile = json.loads((BASE / "ile_alatau_rgi_2024_paired_summary.json").read_text(encoding="utf-8"))
    if ile.get("label_quality_tier") != "provisional_silver_rgi":
        errors.append("Ile cohort must remain provisional_silver_rgi")
    if ile.get("evaluation_status") != "post_hoc_non_independent_not_a_holdout":
        errors.append("Ile cohort must remain non-independent")
    if ile.get("paired_bootstrap", {}).get("n_paired_glaciers", 0) < 15:
        errors.append("Ile paired cohort requires at least 15 glaciers")

    external = json.loads((BASE / "zhetysu_candidate_rgi_2024_summary.json").read_text(encoding="utf-8"))
    if external.get("label_quality_tier") != "provisional_silver_rgi":
        errors.append("external cohort must remain provisional_silver_rgi")
    if external.get("evaluation_status") != "external_geography_but_non_independent_rgi_pseudolabel":
        errors.append("external cohort must not be presented as independent validation")
    if external.get("cohort_selection", {}).get("n_glaciers", 0) < 9:
        errors.append("external provisional cohort requires nine glaciers")
    for source in external.get("source_records", []):
        path = ROOT / str(source.get("path", ""))
        if not path.is_file():
            errors.append(f"missing external source: {path.relative_to(ROOT)}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source.get("sha256"):
            errors.append(f"external source hash mismatch: {path.relative_to(ROOT)}")
    for name in ("ile_alatau_rgi_2024_per_glacier.csv", "zhetysu_candidate_rgi_2024_per_glacier.csv"):
        with (BASE / name).open(newline="", encoding="utf-8") as handle:
            if len(list(csv.DictReader(handle))) == 0:
                errors.append(f"empty per-glacier table: {name}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("PROVISIONAL COHORT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Provisional cohorts valid; strict gold/external evidence gate remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
