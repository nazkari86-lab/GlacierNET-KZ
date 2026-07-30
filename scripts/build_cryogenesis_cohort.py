#!/usr/bin/env python3
"""Build a deterministic CryoGenesis Release 1 evidence cohort."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cryogenesis.divergence import estimate_divergence
from src.cryogenesis.evaluation import cohort_report
from src.cryogenesis.features import (
    MINIMUM_ANCHOR_AREA_KM2,
    extract_physical_records,
    load_feature_fixture,
)
from src.cryogenesis.matching import MatchConfig, match_twins
from src.cryogenesis.passport import (
    build_passport,
    passport_to_dict,
    verify_passport,
)
from src.cryogenesis.schemas import (
    DiscoveryPassport,
    GlacierFeatureRecord,
    SourceAsset,
)
from src.cryogenesis.source_registry import (
    preflight_sources,
    register_required_sources,
    sha256_file,
    verify_sources,
)
from src.cryogenesis.surprise import classify_surprise


def _json_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _matching_config(
    records: list[GlacierFeatureRecord],
) -> MatchConfig:
    available = set.intersection(
        *(set(record.features) for record in records)
    )
    preferred = (
        "anchor_area_km2",
        "elevation_mean_m",
        "elevation_range_m",
        "slope_deg",
        "aspect_sin",
        "aspect_cos",
        "summer_temperature_c",
        "annual_precipitation_m",
        "snow_depth_m",
    )
    selected = [name for name in preferred if name in available]
    if len(selected) < 2:
        raise ValueError("cohort has fewer than two common matching features")
    return MatchConfig(
        feature_weights={name: 1.0 for name in selected},
        maximum_distance=5.0,
        maximum_twins=5,
        minimum_primary_twins=3,
    )


def _build_passports(
    records: list[GlacierFeatureRecord],
    cohort_id: str,
    provenance: tuple[SourceAsset, ...],
) -> list[DiscoveryPassport]:
    config = _matching_config(records)
    by_id = {record.rgi_id: record for record in records}
    passports: list[DiscoveryPassport] = []
    for target in sorted(records, key=lambda record: record.rgi_id):
        match = match_twins(target, records, config)
        divergence = None
        if match.twins and target.outcome is not None:
            twin_outcomes = tuple(
                float(by_id[twin.rgi_id].outcome.value)
                for twin in match.twins
                if by_id[twin.rgi_id].outcome is not None
            )
            weights = tuple(twin.weight for twin in match.twins)
            divergence = estimate_divergence(
                float(target.outcome.value),
                twin_outcomes,
                weights,
            )
        surprise = classify_surprise(
            match_status=match.status,
            target_outcome=(
                float(target.outcome.value)
                if target.outcome is not None
                else None
            ),
            raw_divergence=(
                divergence.raw_divergence if divergence is not None else None
            ),
            comparator_interval=(
                divergence.comparator_interval
                if divergence is not None
                else None
            ),
            measurement_uncertainty=(
                target.outcome.uncertainty
                if target.outcome is not None
                else None
            ),
        )
        passports.append(
            build_passport(
                cohort_id=cohort_id,
                target_rgi_id=target.rgi_id,
                match=match,
                divergence=divergence,
                surprise_class=surprise,
                provenance=provenance,
            )
        )
    return passports


def _feature_rows(
    records: list[GlacierFeatureRecord],
) -> tuple[list[dict[str, Any]], pa.Schema]:
    feature_names = sorted(
        {name for record in records for name in record.features}
    )
    string_features = {
        name
        for name in feature_names
        if any(
            isinstance(record.features.get(name).value, str)
            for record in records
            if record.features.get(name) is not None
        )
    }
    fields = [
        pa.field("rgi_id", pa.string(), nullable=False),
        pa.field("basin_id", pa.string(), nullable=False),
        pa.field("region_id", pa.string(), nullable=False),
        pa.field("split", pa.string(), nullable=False),
        pa.field("anchor_year", pa.int32(), nullable=False),
        pa.field("outcome_year", pa.int32(), nullable=False),
        *[
            pa.field(
                name,
                pa.string() if name in string_features else pa.float64(),
            )
            for name in feature_names
        ],
        pa.field("outcome", pa.float64()),
    ]
    rows: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: item.rgi_id):
        row: dict[str, Any] = {
            "rgi_id": record.rgi_id,
            "basin_id": record.basin_id,
            "region_id": record.region_id,
            "split": record.split,
            "anchor_year": record.anchor_year,
            "outcome_year": record.outcome_year,
            "outcome": (
                float(record.outcome.value)
                if record.outcome is not None
                else None
            ),
        }
        row.update(
            {
                name: (
                    record.features[name].value
                    if name in record.features
                    else None
                )
                for name in feature_names
            }
        )
        rows.append(row)
    return rows, pa.schema(fields)


def _write_bundle(
    output_root: Path,
    records: list[GlacierFeatureRecord],
    provenance: tuple[SourceAsset, ...],
    passports: list[DiscoveryPassport],
    cohort_id: str,
    anchor_year: int,
    outcome_year: int,
    fixture_mode: bool,
    exclusions: list[dict[str, str]],
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    passport_root = output_root / "passports"
    passport_root.mkdir(parents=True, exist_ok=True)
    for stale_passport in passport_root.glob("*.json"):
        stale_passport.unlink()
    for passport in passports:
        payload = passport_to_dict(passport)
        verification = verify_passport(payload)
        if not verification.valid:
            raise ValueError(
                f"generated invalid passport {passport.target_rgi_id}: "
                + ", ".join(verification.errors)
            )
        _json_write(passport_root / f"{passport.target_rgi_id}.json", payload)

    rows, arrow_schema = _feature_rows(records)
    pq.write_table(
        pa.Table.from_pylist(rows, schema=arrow_schema),
        output_root / "features.parquet",
        compression="zstd",
    )
    pd.DataFrame(
        [
            {
                "rgi_id": record.rgi_id,
                "eligible": True,
                "reason": "eligible",
            }
            for record in sorted(records, key=lambda item: item.rgi_id)
        ]
        + [
            {
                "rgi_id": item["rgi_id"],
                "eligible": False,
                "reason": item["reason"],
            }
            for item in sorted(exclusions, key=lambda item: item["rgi_id"])
        ],
        columns=["rgi_id", "eligible", "reason"],
    ).to_csv(output_root / "eligibility.csv", index=False)
    _json_write(
        output_root / "source_assets.json",
        [asdict(asset) for asset in provenance],
    )
    manifest = {
        "schema": "glaciernet-kz.cryogenesis-cohort.v1",
        "builder_version": "1.0.0",
        "cohort_id": cohort_id,
        "anchor_year": anchor_year,
        "outcome_year": outcome_year,
        "git_commit": _git_commit(),
        "fixture_mode": fixture_mode,
        "eligible_glacier_count": len(records),
        "excluded_glacier_count": len(exclusions),
        "input_glacier_count": len(records) + len(exclusions),
        "passport_count": len(passports),
        "scientific_readiness": (
            "cohort_ready"
            if len(records) >= 30 and not fixture_mode
            else "insufficient_cohort_size"
        ),
        "random_seed": 0,
        "feature_columns": list(arrow_schema.names),
        "eligibility_policy": {
            "minimum_anchor_area_km2": MINIMUM_ANCHOR_AREA_KM2,
            "basis": (
                "pre-outcome support of at least 100 positive pixels at "
                "the declared 10 m annual-mask resolution"
            ),
            "outcome_magnitude_filter": False,
        },
    }
    _json_write(output_root / "manifest.json", manifest)
    _json_write(
        output_root / "build_report.json",
        cohort_report(passports, excluded_count=len(exclusions)),
    )

    checksum_lines = []
    for path in sorted(
        item
        for item in output_root.rglob("*")
        if item.is_file() and item.name != "checksums.sha256"
    ):
        checksum_lines.append(
            f"{sha256_file(path)}  {path.relative_to(output_root).as_posix()}"
        )
    (output_root / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--feature-fixture", type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "results/cryogenesis/current",
    )
    parser.add_argument("--anchor-year", type=int, default=2020)
    parser.add_argument("--outcome-year", type=int, default=2024)
    parser.add_argument(
        "--cohort-id", default="ile-alatau-2020-2024-v1"
    )
    args = parser.parse_args()

    if args.preflight:
        report = preflight_sources(PROJECT_ROOT)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if all(
            item["status"] == "ready" for item in report.values()
        ) else 1

    if args.outcome_year <= args.anchor_year:
        parser.error("--outcome-year must be later than --anchor-year")
    if args.feature_fixture:
        records, provenance = load_feature_fixture(
            (PROJECT_ROOT / args.feature_fixture).resolve(),
            PROJECT_ROOT,
        )
        fixture_mode = True
        exclusions: list[dict[str, str]] = []
    else:
        registered = register_required_sources(
            PROJECT_ROOT,
            prediction_years=(args.anchor_year, args.outcome_year),
        )
        verify_sources(registered, PROJECT_ROOT)
        provenance = tuple(source.as_asset() for source in registered)
        records, exclusions = extract_physical_records(
            PROJECT_ROOT, args.anchor_year, args.outcome_year
        )
        fixture_mode = False
    if not records:
        raise ValueError("no eligible glacier records were extracted")
    passports = _build_passports(records, args.cohort_id, provenance)
    _write_bundle(
        args.output_root.resolve(),
        records,
        provenance,
        passports,
        args.cohort_id,
        args.anchor_year,
        args.outcome_year,
        fixture_mode,
        exclusions,
    )
    print(
        json.dumps(
            {
                "status": "built",
                "cohort_id": args.cohort_id,
                "records": len(records),
                "passports": len(passports),
                "output_root": str(args.output_root.resolve()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
