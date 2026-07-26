from __future__ import annotations

from pathlib import Path

import pytest

from scripts.evaluate_provisional_glacier_cohort import (
    metrics_for_table,
    paired_analysis,
    project_relative_or_absolute,
)


def test_paired_bootstrap_uses_glacier_id_and_candidate_minus_control() -> None:
    records = []
    for glacier_id, offset in (("g1", 0.0), ("g2", 0.1)):
        records.extend(
            [
                {
                    "glacier_id": glacier_id,
                    "area_class": "small",
                    "model": "control",
                    "hard_dice": 0.6 + offset,
                    "hard_iou": 0.5 + offset,
                    "precision": 0.8,
                    "recall": 0.5,
                    "area_error_km2": -2.0,
                },
                {
                    "glacier_id": glacier_id,
                    "area_class": "small",
                    "model": "s1",
                    "hard_dice": 0.7 + offset,
                    "hard_iou": 0.6 + offset,
                    "precision": 0.9,
                    "recall": 0.7,
                    "area_error_km2": -1.0,
                },
            ]
        )
    result = paired_analysis(records, seed=42)
    assert result["n_paired_glaciers"] == 2
    assert result["candidate_minus_control"]["hard_iou"]["estimate"] == pytest.approx(0.1)
    assert result["candidate_minus_control"]["absolute_area_error_km2"]["estimate"] == -1.0
    assert result["paired_tests"]["hard_iou"]["candidate_win_rate"] == 1.0


def test_external_path_is_preserved_for_smoke_output() -> None:
    assert project_relative_or_absolute(Path("/tmp/cohort.csv")) == "/tmp/cohort.csv"


def test_boundary_metric_names_and_unbounded_status_are_explicit() -> None:
    metrics = metrics_for_table({"hausdorff95": float("inf"), "assd": float("inf")})
    assert metrics["hausdorff95_m"] == float("inf")
    assert metrics["assd_m"] == float("inf")
    assert metrics["boundary_distance_status"] == "unbounded"
