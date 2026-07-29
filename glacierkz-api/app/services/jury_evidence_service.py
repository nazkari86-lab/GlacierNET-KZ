"""Read-only, evidence-bounded jury summary for the local release."""

from __future__ import annotations

import csv
import json
from typing import Any

from app.services.glacier_registry_service import CORE_DIR
from app.services.scientific_evidence_service import scientific_evidence


def _read(relative: str) -> dict[str, Any]:
    with (CORE_DIR / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_optional(relative: str) -> dict[str, Any] | None:
    path = CORE_DIR / relative
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _machine_assisted_label_pack() -> dict[str, Any]:
    """Derive pack facts from its signed-on-disk manifest, never constants."""
    manifest = _read_optional("benchmarks/v2/annotations/machine_assisted/manifest.json")
    if not manifest:
        return {
            "status": "unavailable",
            "tasks": 0,
            "glaciers": 0,
            "years": [],
            "purpose": "machine-assisted pack has not been generated",
        }
    queue_relative = manifest.get("queue", {}).get("path")
    queue_path = CORE_DIR / str(queue_relative) if queue_relative else None
    rows: list[dict[str, str]] = []
    if queue_path and queue_path.is_file():
        with queue_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    all_provisional = bool(rows) and all(
        row.get("label_tier") == "machine_assisted_rgi_inventory"
        and row.get("annotation_status") == "provisional_not_gold"
        and row.get("human_review_status") == "not_reviewed"
        for row in rows
    )
    return {
        "status": "available_provisional_not_gold" if all_provisional else "invalid_or_incomplete",
        "tasks": len(rows),
        "glaciers": len({row.get("glacier_id") for row in rows if row.get("glacier_id")}),
        "years": sorted({int(row["year"]) for row in rows if row.get("year", "").isdigit()}),
        "purpose": manifest.get("purpose", "Technical QA and annotation bootstrap only"),
    }


def jury_evidence() -> dict[str, Any]:
    claims = _read("benchmarks/v2/claims_registry.json")
    temporal = _read("results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json")
    zhetysu = _read("benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_summary.json")
    readiness = _read("results/decision_readiness_summary.json")
    external_readiness = _read_optional("benchmarks/v2/readiness/evidence_readiness.json")
    required = [
        "README.md",
        "CITATION.cff",
        "docs/DEMO_WALKTHROUGH.md",
        "docs/RELEASE_PACKAGE.md",
        "docs/REPRODUCIBILITY.md",
        "results/data_manifest.json",
        "results/decision_readiness_summary.json",
    ]
    status_counts: dict[str, int] = {}
    for claim in claims["claims"]:
        status_counts[claim["status"]] = status_counts.get(claim["status"], 0) + 1
    metrics = temporal.get("hard_metrics", {})
    strict = readiness["strict_trend"]
    return {
        "schema": "glaciernet-kz.jury-evidence.v1",
        "claim_policy": claims["policy"],
        "release_checks": {
            "local_package_complete": all((CORE_DIR / path).is_file() for path in required),
            "required_artifact_count": len(required),
        },
        "claim_status_counts": status_counts,
        "supported_now": [
            {
                "title": "Temporal one-AOI silver benchmark",
                "value": {"hard_dice": metrics.get("hard_dice"), "hard_iou": metrics.get("hard_iou")},
                "scope": temporal["generalisation_scope"],
            },
            {
                "title": "Automatic regional observation scan",
                "value": "real local lake inventories, RGI geometry and historical-event context",
                "scope": "follow-up screening only; no event probability",
            },
        ],
        "honest_negative_result": {
            "title": "Provisional external-geography stress test",
            "hard_dice": zhetysu["metrics_bootstrap"]["hard_dice"],
            "area_error_percent": zhetysu["metrics_bootstrap"]["area_error_percent"],
            "meaning": "The current model does not demonstrate external generalisation; this is a useful failure signal, not a hidden result.",
        },
        "strict_trend": {
            "n_years": strict["n_years"],
            "slope_km2_per_year": strict["slope_km2_per_year"],
            "p_value": strict["p_value"],
            "significant": strict["significant"],
            "meaning": "The local strict trend is exploratory and not statistically significant.",
        },
        "blocked_until_external_work": [
            claim for claim in claims["claims"] if claim["status"] == "blocked_external_evidence"
        ],
        "automation_readiness": {
            "available": external_readiness is not None,
            "machine_assisted_label_pack": _machine_assisted_label_pack(),
            "claims": external_readiness.get("claims", []) if external_readiness else [],
        },
        "scientific_evidence": scientific_evidence(),
        "sources": [
            "benchmarks/v2/claims_registry.json",
            "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json",
            "benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_summary.json",
            "results/decision_readiness_summary.json",
        ],
    }
