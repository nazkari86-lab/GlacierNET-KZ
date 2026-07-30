"""Readiness gate for retrospective active-evidence acquisition evaluation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def build_active_evidence_readiness(project_root: str | Path) -> dict[str, Any]:
    """Inspect only persisted real rows; never manufacture benchmark outcomes."""
    root = Path(project_root)
    base = root / "benchmarks/central_asia_cascade"
    review_path = base / "tables/event_review_queue.csv"
    replay_path = base / "tables/event_replay.csv"
    value_path = base / "tables/observation_value.csv"
    manifest_path = base / "manifests/event_replay.json"
    review = _rows(review_path)
    replay = _rows(replay_path)
    values = _rows(value_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}

    strict_events = [
        row
        for row in review
        if _truthy(row.get("primary_source_verified")) and _truthy(row.get("eligible_for_strict_benchmark"))
    ]
    realised_values = [
        row for row in values if row.get("realised_loss_reduction", "").strip() and row.get("snapshot_id", "").strip()
    ]
    immutable_replays = [
        row for row in replay if row.get("snapshot_id", "").strip() and row.get("manifest_sha256", "").strip()
    ]
    controls = manifest.get("non_event_controls", [])
    blockers = []
    if not strict_events:
        blockers.append("no_primary_source_verified_strict_events")
    if not controls:
        blockers.append("no_verified_non_event_controls")
    if not immutable_replays:
        blockers.append("no_immutable_pre_event_replay_snapshots")
    if not realised_values:
        blockers.append("no_realised_observation_loss_reduction_rows")

    return {
        "schema": "glaciernet-kz.active-evidence-readiness.v1",
        "status": "evaluation_ready" if not blockers else "blocked_evidence_incomplete",
        "performance_metrics_computed": not blockers,
        "counts": {
            "database_cited_event_records": len(review),
            "primary_source_verified_strict_events": len(strict_events),
            "verified_non_event_controls": len(controls),
            "immutable_pre_event_replays": len(immutable_replays),
            "realised_observation_value_rows": len(realised_values),
        },
        "blockers": blockers,
        "artifacts": [
            {
                "path": str(path.relative_to(root)),
                "exists": path.is_file(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
            for path in (review_path, replay_path, value_path, manifest_path)
        ],
        "claim_allowed": (
            "retrospective active-evidence acquisition performance"
            if not blockers
            else "implemented leakage-safe protocol and measured evidence readiness"
        ),
        "claim_not_allowed": (
            "observation-policy performance, calibrated event probability or warning skill "
            "until every blocker is resolved"
        ),
    }
