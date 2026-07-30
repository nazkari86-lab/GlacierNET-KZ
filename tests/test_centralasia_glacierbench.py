from __future__ import annotations

import json

import numpy as np
import pytest

from src.centralasia_benchmark.active_evidence import build_active_evidence_readiness
from src.centralasia_benchmark.metrics import (
    event_control_metrics,
    physical_consistency_metrics,
    temporal_stability_metrics,
)
from src.centralasia_benchmark.registry import build_source_registry
from src.centralasia_benchmark.report import build_benchmark_report


def test_registry_never_promotes_missing_sources(tmp_path):
    rows = build_source_registry(tmp_path)
    assert rows
    assert all(row["state"] == "missing" for row in rows)
    assert all(row["available"] is False for row in rows)


def test_temporal_stability_flags_large_real_area_jump():
    metrics = temporal_stability_metrics([10.0, 9.8, 4.0])
    assert metrics["n_observations"] == 3
    assert metrics["implausible_jump_count"] == 1
    assert metrics["stability_fraction"] == pytest.approx(0.5)


def test_physical_consistency_keeps_missing_layers_explicit():
    metrics = physical_consistency_metrics(glacier_probability=np.ones((2, 2)))
    assert metrics["status"] == "blocked_missing_physical_layers"
    assert metrics["thinning_support_fraction"] is None
    assert metrics["motion_support_fraction"] is None


def test_event_control_auc_uses_observed_pairs():
    metrics = event_control_metrics(
        [
            {"event": 1, "score": 0.9},
            {"event": 1, "score": 0.8},
            {"event": 0, "score": 0.3},
            {"event": 0, "score": 0.2},
        ]
    )
    assert metrics["roc_auc"] == 1.0
    assert metrics["n_events"] == metrics["n_controls"] == 2


def test_report_exposes_real_metrics_and_claim_boundaries(tmp_path):
    temporal_path = tmp_path / "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json"
    temporal_path.parent.mkdir(parents=True)
    temporal_path.write_text(
        json.dumps(
            {
                "label_quality_tier": "silver",
                "generalisation_scope": "fixture",
                "hard_metrics": {"hard_dice": 0.8, "hard_iou": 0.67},
            }
        ),
        encoding="utf-8",
    )
    report = build_benchmark_report(tmp_path)
    assert report["benchmark_version"] == "0.4.0"
    temporal = next(track for track in report["tracks"] if track["id"] == "temporal_segmentation")
    assert temporal["status"] == "measured"
    assert temporal["category"] == "model_evaluation"
    assert temporal["headline_metrics"]["hard_dice"] == 0.8
    assert report["summary"]["reference_evidence_total"] == 4
    assert report["summary"]["model_evaluations_total"] == 5
    active = next(track for track in report["tracks"] if track["id"] == "active_evidence_acquisition")
    assert active["status"] == "blocked_evidence_incomplete"
    assert active["metrics"]["primary_source_verified_strict_events"] == 0
    assert report["policy"]["no_synthetic_metrics"] is True
    assert "independent expert gold-label accuracy" in report["claims_not_unlocked"]


def test_active_evidence_gate_counts_only_verified_real_rows(tmp_path):
    tables = tmp_path / "benchmarks/central_asia_cascade/tables"
    manifests = tmp_path / "benchmarks/central_asia_cascade/manifests"
    tables.mkdir(parents=True)
    manifests.mkdir(parents=True)
    (tables / "event_review_queue.csv").write_text(
        "event_id,primary_source_verified,eligible_for_strict_benchmark\nE1,true,true\nE2,false,true\n",
        encoding="utf-8",
    )
    (tables / "event_replay.csv").write_text(
        "snapshot_id,manifest_sha256\nS1,abc\n",
        encoding="utf-8",
    )
    (tables / "observation_value.csv").write_text(
        "snapshot_id,realised_loss_reduction\nS1,0.25\n",
        encoding="utf-8",
    )
    (manifests / "event_replay.json").write_text(
        json.dumps({"non_event_controls": [{"basin_id": "C1"}]}),
        encoding="utf-8",
    )
    readiness = build_active_evidence_readiness(tmp_path)
    assert readiness["status"] == "evaluation_ready"
    assert readiness["performance_metrics_computed"] is True
    assert readiness["counts"]["primary_source_verified_strict_events"] == 1
