from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from scripts.evaluate_temporal_benchmark import benchmark_v2_metrics
from scripts.validate_temporal_consistency import build_temporal_rows, classify_change
from src.acquisition_quality import acquisition_decision, assess_sentinel2_scene
from src.benchmark_metrics import (
    area_metrics,
    bootstrap_confidence_intervals,
    bootstrap_paired_difference,
    boundary_segmentation_metrics,
    calibrate_threshold,
    hard_segmentation_metrics,
)
from src.benchmark_splits import cross_region_split, glacier_holdout_split, validate_group_manifest


def test_hard_metrics_share_one_thresholded_confusion_matrix():
    true = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    prob = np.array([[0.9, 0.4], [0.8, 0.1]])
    result = hard_segmentation_metrics(true, prob, threshold=0.5)
    assert result == {
        "threshold": 0.5,
        "hard_dice": 0.5,
        "hard_iou": 1 / 3,
        "precision": 0.5,
        "recall": 0.5,
        "tp": 1,
        "fp": 1,
        "fn": 1,
        "tn": 1,
    }


def test_acquisition_quality_detects_snow_cloud_shadow_and_nodata():
    bands = np.full((6, 2, 4), 0.15, dtype=np.float32)
    bands[:, 0, 0] = 0  # no data
    bands[0:3, 0, 1] = 0.5
    bands[3, 0, 1] = 0.4
    bands[5, 0, 1] = 0.3  # cloud
    bands[0:3, 0, 2] = 0.03
    bands[3, 0, 2] = 0.04  # shadow
    bands[1, 0, 3] = 0.6
    bands[5, 0, 3] = 0.05  # snow
    result = assess_sentinel2_scene(bands)
    assert result["nodata_fraction"] == pytest.approx(1 / 8)
    assert result["cloud_fraction"] > 0
    assert result["shadow_fraction"] > 0
    assert result["snow_fraction"] > 0
    assert result["off_glacier_snow_available"] is False
    status, reasons = acquisition_decision(result)
    assert status == "reject"
    assert reasons


def test_boundary_and_area_metrics_use_physical_units():
    true = np.zeros((7, 7), dtype=np.uint8)
    pred = np.zeros((7, 7), dtype=np.float32)
    true[2:5, 2:5] = 1
    pred[2:5, 3:6] = 1
    boundary = boundary_segmentation_metrics(true, pred, pixel_size=10, tolerance_pixels=1)
    area = area_metrics(true, pred, pixel_area_m2=100)
    assert 0 < boundary["boundary_f1"] <= 1
    assert boundary["hausdorff95"] == pytest.approx(10)
    assert boundary["assd"] > 0
    assert area["true_area_km2"] == pytest.approx(0.0009)
    assert area["area_error_km2"] == pytest.approx(0)


def test_missing_prediction_has_infinite_surface_distance():
    true = np.ones((3, 3), dtype=np.uint8)
    pred = np.zeros((3, 3), dtype=np.float32)
    result = boundary_segmentation_metrics(true, pred)
    assert result["boundary_f1"] == 0
    assert math.isinf(result["hausdorff95"])
    assert math.isinf(result["assd"])


def test_threshold_is_selected_by_declared_validation_objective():
    true = np.array([1, 1, 0, 0], dtype=np.uint8)
    prob = np.array([0.9, 0.6, 0.55, 0.1])
    result = calibrate_threshold(true, prob, thresholds=[0.5, 0.6, 0.7], pixel_area_m2=100)
    assert result["selection_split"] == "validation"
    assert result["selected_threshold"] == 0.6
    assert result["selected_metrics"]["hard_dice"] == 1


def test_temporal_evaluator_freezes_validation_threshold_for_test():
    class FakeModel:
        def __init__(self):
            self.calls = 0

        def predict(self, values, **kwargs):
            self.calls += 1
            return values

    validation_labels = np.array([1, 1, 0, 0], dtype=np.uint8)
    validation_probabilities = np.array([0.9, 0.6, 0.55, 0.1])
    test_labels = np.array([1, 0], dtype=np.uint8)
    test_probabilities = np.array([0.65, 0.58])
    result = benchmark_v2_metrics(
        FakeModel(),
        validation_probabilities,
        validation_labels,
        test_probabilities,
        test_labels,
        batch_size=2,
        pixel_area_m2=100,
    )
    assert result["threshold_calibration"]["selected_threshold"] == 0.6
    assert result["hard_metrics"]["threshold"] == 0.6
    assert result["hard_metrics"]["hard_dice"] == 1


def test_bootstrap_is_glacier_level_reproducible_and_paired():
    rows = [
        {"glacier_id": "A", "hard_dice": 0.7, "hard_iou": 0.6, "area_error_percent": 10, "s2": 0.7, "s1": 0.75},
        {"glacier_id": "B", "hard_dice": 0.9, "hard_iou": 0.8, "area_error_percent": 5, "s2": 0.9, "s1": 0.92},
    ]
    intervals = bootstrap_confidence_intervals(rows, n_resamples=100, seed=7)
    assert intervals["hard_dice"]["estimate"] == pytest.approx(0.8)
    assert intervals["hard_dice"]["n_glaciers"] == 2
    paired = bootstrap_paired_difference(rows, baseline_key="s2", candidate_key="s1", n_resamples=100, seed=7)
    assert paired["estimate"] == pytest.approx(0.035)
    assert paired["ci_lower"] > 0
    assert paired["statistically_confirmed"] is True


def test_glacier_holdout_is_disjoint_and_deterministic():
    ids = [f"KZ_{index:03d}" for index in range(10)]
    first = glacier_holdout_split(ids, seed=11)
    second = glacier_holdout_split(reversed(ids), seed=11)
    assert first == second
    validate_group_manifest(first)
    assert set(first["train_glaciers"]).isdisjoint(first["test_glaciers"])


def test_group_manifest_rejects_leakage():
    with pytest.raises(ValueError, match="leakage"):
        validate_group_manifest(
            {
                "train_glaciers": ["KZ_001"],
                "validation_glaciers": ["KZ_002"],
                "test_glaciers": ["KZ_001"],
            }
        )


def test_cross_region_split_is_external():
    manifest = cross_region_split(
        {"ILE_1": "Ile Alatau", "ILE_2": "Ile Alatau", "JET_1": "Zhetysu Alatau"},
        train_region="Ile Alatau",
        test_region="Zhetysu Alatau",
    )
    assert manifest["train_glaciers"] == ["ILE_1", "ILE_2"]
    assert manifest["test_glaciers"] == ["JET_1"]


@pytest.mark.parametrize(
    ("change", "status"),
    [(0.05, "normal"), (0.10, "review"), (0.20, "suspicious"), (0.31, "reject")],
)
def test_temporal_change_thresholds(change, status):
    assert classify_change(change)[0] == status


def test_current_style_temporal_jump_is_rejected(tmp_path: Path):
    area_rows = [
        {"year": "2017", "sensor": "Sentinel-2", "method": "RF", "area_km2": "324.93"},
        {"year": "2018", "sensor": "Sentinel-2", "method": "RF", "area_km2": "859.19"},
    ]
    quality_rows = [
        {"year": "2017", "include_in_strict_trend": "True"},
        {"year": "2018", "include_in_strict_trend": "True"},
    ]
    rows = build_temporal_rows(area_rows, quality_rows, sensor="Sentinel-2", method="RF")
    assert rows[1]["status"] == "reject"
    assert float(rows[1]["relative_change"]) == pytest.approx(1.644231)
    assert "missing acquisition QA" in str(rows[1]["reason"])


def test_temporal_output_contract_has_requested_fields():
    output = Path("results/tables/temporal_anomalies.csv")
    if not output.exists():
        pytest.skip("generated report not built yet")
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert set(rows[0]) == {
        "year",
        "area_km2",
        "previous_area_km2",
        "relative_change",
        "z_score",
        "snow_fraction",
        "cloud_fraction",
        "status",
        "reason",
    }


def test_benchmark_v2_structure_passes_but_strict_evidence_gate_blocks():
    root = Path(__file__).resolve().parent.parent
    validator = root / "scripts/validate_benchmark_v2.py"
    structure = subprocess.run(
        [sys.executable, str(validator), "--allow-incomplete"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert structure.returncode == 0, structure.stdout + structure.stderr
    assert "EVIDENCE INCOMPLETE" in structure.stdout

    strict = subprocess.run(
        [sys.executable, str(validator)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
    assert "benchmark evidence blocker" in strict.stdout
