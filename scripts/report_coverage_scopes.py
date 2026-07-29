#!/usr/bin/env python3
"""Report honest repository and production-scope Python coverage gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "coverage_scopes.json"


def _coverage(summary_rows: list[dict[str, Any]]) -> dict[str, float | int]:
    statements = sum(int(row.get("num_statements", 0)) for row in summary_rows)
    covered = sum(int(row.get("covered_lines", 0)) for row in summary_rows)
    percent = 100.0 if statements == 0 else covered * 100.0 / statements
    return {"covered_lines": covered, "num_statements": statements, "percent": round(percent, 2)}


def calculate_scopes(coverage: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    files = coverage.get("files", {})
    if not isinstance(files, dict) or not files:
        raise ValueError("Coverage JSON has no per-file data")
    research = set(config.get("research_modules", []))
    all_rows = [item.get("summary", {}) for item in files.values()]
    production_rows = [item.get("summary", {}) for path, item in files.items() if path not in research]
    research_rows = [item.get("summary", {}) for path, item in files.items() if path in research]
    classified_research = sorted(path for path in files if path in research)
    return {
        "schema": "glaciernet-kz.coverage-report.v1",
        "repository": _coverage(all_rows),
        "production_scope": _coverage(production_rows),
        "research_scaffolds": _coverage(research_rows),
        "classification": {
            "research_files_measured": classified_research,
            "research_files_declared_but_not_imported": sorted(research - set(files)),
            "production_files_measured": len(files) - len(classified_research),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, default=ROOT / "coverage.json")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repository-min", type=float)
    parser.add_argument("--production-min", type=float)
    args = parser.parse_args()

    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = calculate_scopes(coverage, config)
    policy = config.get("policy", {})
    repository_min = (
        args.repository_min if args.repository_min is not None else float(policy.get("repository_minimum_percent", 0))
    )
    production_min = (
        args.production_min
        if args.production_min is not None
        else float(policy.get("production_scope_minimum_percent", 0))
    )
    report["gates"] = {
        "repository": {
            "minimum_percent": repository_min,
            "passed": report["repository"]["percent"] >= repository_min,
        },
        "production_scope": {
            "minimum_percent": production_min,
            "passed": report["production_scope"]["percent"] >= production_min,
        },
    }
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0 if all(gate["passed"] for gate in report["gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
