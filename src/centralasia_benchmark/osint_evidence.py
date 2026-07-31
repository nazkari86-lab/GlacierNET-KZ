"""Leakage-safe readiness gate for future OSINT event prediction."""

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
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes"}


def build_osint_prediction_readiness(project_root: str | Path) -> dict[str, Any]:
    """Count only persisted, source-reviewed labels and pre-event snapshots."""
    root = Path(project_root)
    base = root / "benchmarks/osint_event_radar"
    event_path = base / "tables/events.csv"
    control_path = base / "tables/controls.csv"
    snapshot_path = base / "manifests/pre_event_snapshots.jsonl"
    protocol_path = base / "protocol.md"
    events = _rows(event_path)
    controls = _rows(control_path)

    verified_events = [
        row
        for row in events
        if _truthy(row.get("primary_source_verified"))
        and _truthy(row.get("eligible_for_strict_benchmark"))
        and row.get("event_time", "").strip()
    ]
    verified_controls = [
        row
        for row in controls
        if _truthy(row.get("absence_window_verified"))
        and _truthy(row.get("coverage_matched"))
        and row.get("basin_id", "").strip()
    ]
    snapshots: list[dict[str, Any]] = []
    if snapshot_path.is_file():
        for line in snapshot_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                snapshots.append(json.loads(line))
            except json.JSONDecodeError:
                snapshots.append({})
    immutable_snapshots = [
        row
        for row in snapshots
        if row.get("snapshot_id")
        and row.get("cutoff_time")
        and row.get("manifest_sha256")
        and row.get("split") in {"development", "temporal_test", "external_test"}
    ]
    split_names = {str(row.get("split")) for row in immutable_snapshots}
    source_ids = {row.get("source_id", "").strip() for row in verified_events if row.get("source_id", "").strip()}

    blockers = []
    if not verified_events:
        blockers.append("no_primary_source_verified_events")
    if not verified_controls:
        blockers.append("no_coverage_matched_non_event_controls")
    if not immutable_snapshots:
        blockers.append("no_immutable_pre_event_snapshots")
    if not {"development", "temporal_test", "external_test"}.issubset(split_names):
        blockers.append("development_temporal_external_splits_incomplete")
    if len(source_ids) < 2:
        blockers.append("fewer_than_two_independent_event_sources")

    artifacts = []
    for path in (protocol_path, event_path, control_path, snapshot_path):
        artifacts.append(
            {
                "path": str(path.relative_to(root)),
                "exists": path.is_file(),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size if path.is_file() else None,
            }
        )
    return {
        "schema": "glaciernet-kz.osint-prediction-readiness.v1",
        "status": "evaluation_ready" if not blockers else "blocked_evidence_incomplete",
        "counts": {
            "event_rows": len(events),
            "strict_verified_events": len(verified_events),
            "strict_verified_controls": len(verified_controls),
            "immutable_pre_event_snapshots": len(immutable_snapshots),
            "independent_event_sources": len(source_ids),
        },
        "blockers": blockers,
        "artifacts": artifacts,
        "claim_allowed": (
            "retrospective OSINT detection performance on frozen splits"
            if not blockers
            else "implemented source-backed Event Radar and measured prediction-evidence readiness"
        ),
        "claim_not_allowed": (
            "news-based event forecast, calibrated GLOF probability, operational warning skill, "
            "or claimed lead time until every blocker is resolved and metrics are computed"
        ),
    }
