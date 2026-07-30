from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.routers.benchmark import benchmark_sources, benchmark_tracks, current_benchmark  # noqa: E402
from app.services import benchmark_service  # noqa: E402


def test_benchmark_api_reads_generated_report(tmp_path, monkeypatch):
    report_path = tmp_path / "benchmarks/centralasia_glacierbench/current/report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        json.dumps(
            {
                "schema": "centralasia-glacierbench.report.v1",
                "benchmark_name": "CentralAsia-GlacierBench",
                "sources": [{"id": "real-source"}],
                "tracks": [{"id": "real-track"}],
                "summary": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark_service, "_project_root", lambda: tmp_path)

    report = current_benchmark()
    assert report["status"] == "ready"
    assert benchmark_sources()["sources"][0]["id"] == "real-source"
    assert benchmark_tracks()["tracks"][0]["id"] == "real-track"


def test_benchmark_api_never_fabricates_missing_report(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_service, "_project_root", lambda: tmp_path)
    report = current_benchmark()
    assert report["status"] == "not_built"
    assert report["sources"] == []
    assert report["tracks"] == []
