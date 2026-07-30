"""Release metadata must stay synchronized across Python, API, web, and citation."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _match(path: Path, pattern: str) -> str:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, f"Version marker not found in {path}"
    return match.group(1)


def test_release_versions_are_synchronized() -> None:
    package = json.loads((ROOT / "glacierkz-web" / "package.json").read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / "benchmarks/centralasia_glacierbench/protocol.json").read_text(encoding="utf-8"))
    report = json.loads((ROOT / "benchmarks/centralasia_glacierbench/current/report.json").read_text(encoding="utf-8"))
    versions = {
        "python": _match(ROOT / "pyproject.toml", r'^version = "([^"]+)"$'),
        "api": _match(
            ROOT / "glacierkz-api" / "app" / "main.py",
            r'^PROJECT_VERSION = "([^"]+)"$',
        ),
        "web": package["version"],
        "citation": _match(ROOT / "CITATION.cff", r"^version: ([^\s]+)$"),
        "benchmark_protocol": protocol["version"],
        "benchmark_report": report["benchmark_version"],
    }

    assert len(set(versions.values())) == 1, versions
