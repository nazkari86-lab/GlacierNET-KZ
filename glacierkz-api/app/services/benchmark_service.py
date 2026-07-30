"""Read-only access to the generated CentralAsia-GlacierBench report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils import resolve_core_dir


def _project_root() -> Path:
    configured = resolve_core_dir(__file__)
    for candidate in (configured, configured.parent):
        if (candidate / "benchmarks").is_dir():
            return candidate
    return configured


def benchmark_report() -> dict[str, Any]:
    root = _project_root()
    path = root / "benchmarks/centralasia_glacierbench/current/report.json"
    if not path.is_file():
        return {
            "schema": "centralasia-glacierbench.report.v2",
            "benchmark_name": "CentralAsia-GlacierBench",
            "status": "not_built",
            "sources": [],
            "tracks": [],
            "summary": {
                "sources_total": 0,
                "sources_local": 0,
                "sources_verified": 0,
                "sources_metadata_only": 0,
                "sources_missing": 0,
                "tracks_total": 0,
                "tracks_data_ready": 0,
                "tracks_blocked": 0,
                "model_evaluations_total": 0,
                "model_evaluations_measured": 0,
                "reference_evidence_total": 0,
                "reference_evidence_available": 0,
                "decision_support_evaluations_total": 0,
                "decision_support_evaluations_ready": 0,
            },
            "build_command": "python scripts/build_centralasia_glacierbench.py",
        }
    with path.open(encoding="utf-8") as handle:
        report = json.load(handle)
    report["status"] = "ready"
    return report
