"""Artifact-bound scientific evidence for the non-promotional cockpit.

This service formats already measured local artifacts.  It intentionally does
not calculate performance, infer validation, or upgrade provisional records.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.utils import resolve_core_dir


def _resolve_project_root() -> Path:
    """Find the repository root even when an API-only test sets CORE_DIR.

    Most runtime entry points set ``CORE_DIR`` to the repository root.  Some
    focused API test environments intentionally set it to ``glacierkz-api``;
    the scientific artifacts are one level above that directory.  Resolve only
    an existing manifest and otherwise preserve the configured base, rather
    than guessing or fabricating evidence.
    """
    configured = resolve_core_dir(__file__)
    for candidate in (configured, configured.parent):
        if (candidate / "benchmarks" / "v2" / "claims_registry.json").is_file():
            return candidate
    return configured


CORE_DIR = _resolve_project_root()


def _read_json(relative_path: str) -> dict[str, Any]:
    path = CORE_DIR / relative_path
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _artifact(relative_path: str) -> dict[str, str | bool | None]:
    """Expose existence and digest; never claim a missing file as evidence."""
    path = CORE_DIR / relative_path
    if not path.is_file():
        return {"path": relative_path, "exists": False, "sha256": None}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": relative_path, "exists": True, "sha256": digest}


def _claim(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "status": record["status"],
        "claim": record["claim"],
        "scope": record["scope"],
        "artifacts": [_artifact(str(path)) for path in record.get("evidence", [])],
    }


def scientific_evidence() -> dict[str, Any]:
    """Return a compact, typed view of real scientific artifacts and limits."""
    claims = _read_json("benchmarks/v2/claims_registry.json")
    temporal = _read_json("results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json")
    paired = _read_json("benchmarks/v2/provisional/ile_alatau_rgi_2024_paired_summary.json")
    cross_region = _read_json("benchmarks/v2/manifests/cross_region.json")

    return {
        "schema": "glaciernet-kz.scientific-evidence.v1",
        "claim_policy": claims["policy"],
        "claim_registry": [_claim(record) for record in claims["claims"]],
        "temporal_holdout": {
            "evaluation_protocol": temporal["evaluation_protocol"],
            "generalisation_scope": temporal["generalisation_scope"],
            "label_quality_tier": temporal["label_quality_tier"],
            "label_provenance": temporal["label_provenance"],
            "splits": {
                "train_years": temporal["train_years"],
                "validation_years": temporal["validation_years"],
                "test_years": temporal["test_years"],
            },
            "hard_metrics": temporal["hard_metrics"],
            "threshold_calibration": {
                "selection_split": temporal["threshold_calibration"]["selection_split"],
                "objective": temporal["threshold_calibration"]["objective"],
                "selected_threshold": temporal["threshold_calibration"]["selected_threshold"],
            },
            "glacier_level_ci_status": temporal["bootstrap_status"],
            "boundary_metrics_status": temporal["boundary_metrics_status"],
            "claims_allowed": temporal["claims_allowed"],
            "claims_not_allowed": temporal["claims_not_allowed"],
            "artifacts": [
                _artifact("results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json"),
                {
                    "path": temporal["model_path"],
                    "exists": (CORE_DIR / temporal["model_path"]).exists(),
                    "sha256": temporal["model_artifact_sha256"],
                },
            ],
        },
        "paired_glacier_diagnostic": {
            "label_quality_tier": paired["label_quality_tier"],
            "evaluation_status": paired["evaluation_status"],
            "cohort_selection": paired["cohort_selection"],
            "metrics": paired["paired_analysis"]["candidate_minus_control"],
            "paired_tests": paired["paired_analysis"]["paired_tests"],
            "claims_not_allowed": paired["claims_not_allowed"],
            "artifacts": [
                _artifact("benchmarks/v2/provisional/ile_alatau_rgi_2024_paired_summary.json"),
                _artifact(paired["per_glacier_table"]),
            ],
        },
        "external_generalisation": {
            "status": "blocked_external_evidence" if not cross_region["ready"] else "external_evidence_available",
            "test_region": cross_region["test_region"],
            "label_quality_tier_required": cross_region["label_quality_tier"],
            "blocked_reason": cross_region.get("blocked_reason"),
            "artifact": _artifact("benchmarks/v2/manifests/cross_region.json"),
        },
    }
