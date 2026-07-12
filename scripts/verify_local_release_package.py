#!/usr/bin/env python3
"""Verify that the local GitHub release package has its required public artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = (
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "docs/DEMO_WALKTHROUGH.md",
    "docs/RELEASE_PACKAGE.md",
    "docs/REPRODUCIBILITY.md",
    "results/data_quality_report.json",
    "results/decision_readiness_summary.json",
    "results/tables/decision_ready_area_timeseries.csv",
    "results/tables/year_quality_scores.csv",
    "results/tables/random_forest_feature_importance.csv",
    "results/tables/eda_sentinel2_2020.csv",
)


def missing_required_paths(root: Path = ROOT) -> list[str]:
    return [path for path in REQUIRED_PATHS if not (root / path).is_file()]


def main() -> int:
    missing = missing_required_paths()
    if missing:
        print("LOCAL RELEASE PACKAGE FAILED")
        for path in missing:
            print(f"  - missing: {path}")
        return 1

    print("Local release package is complete.")
    print("External release blockers: GitHub publication, domain-expert review, stakeholder pilot/LOI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
