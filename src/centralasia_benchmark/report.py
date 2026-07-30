"""Build an evidence-bound CentralAsia-GlacierBench report."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .active_evidence import build_active_evidence_readiness
from .hma_reference import build_hma_reference_metrics
from .reference_tracks import (
    build_event_colocation_metrics,
    build_hugonnet_reference_metrics,
)
from .registry import build_source_registry


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _artifact(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        return {"path": relative, "exists": False, "sha256": None}
    return {
        "path": relative,
        "exists": True,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _source_state(registry: list[dict[str, object]], source_id: str) -> str:
    return str(next(row["state"] for row in registry if row["id"] == source_id))


def _estimate(metric: Any) -> float | int | None:
    if isinstance(metric, dict):
        value = metric.get("estimate")
        return value if isinstance(value, (float, int)) else None
    return metric if isinstance(metric, (float, int)) else None


def _itslive_metrics(path: Path) -> dict[str, Any]:
    import pandas as pd

    frame = pd.read_parquet(path)
    required = {
        "rgi_id",
        "observations_valid",
        "velocity_m_per_year_median",
        "velocity_m_per_year_p90",
    }
    if frame.empty or not required.issubset(frame.columns):
        raise ValueError("ITS_LIVE sample table is empty or incomplete")
    return {
        "sampled_glaciers": int(frame["rgi_id"].nunique()),
        "valid_velocity_observations": int(frame["observations_valid"].sum()),
        "median_of_glacier_median_velocity_m_per_year": float(frame["velocity_m_per_year_median"].median()),
        "median_of_glacier_p90_velocity_m_per_year": float(frame["velocity_m_per_year_p90"].median()),
        "sampling_geometry": "one RGI7 centroid point per selected ITS_LIVE cube",
    }


def build_benchmark_report(project_root: str | Path) -> dict[str, Any]:
    """Assemble model evaluations and reference evidence without conflating them."""
    root = Path(project_root).resolve()
    registry = build_source_registry(root)
    temporal_path = "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json"
    external_path = "benchmarks/v2/provisional/inventory_guided_decoder_2024.json"
    temporal = _read_json(root / temporal_path)
    external = _read_json(root / external_path)
    sentinel1_path = "results/ablation_unet_sentinel2_terrain_s1_2017_2024.json"
    sentinel1 = _read_json(root / sentinel1_path)

    tracks: list[dict[str, Any]] = []
    if temporal:
        tracks.append(
            {
                "id": "temporal_segmentation",
                "title": "Temporal glacier segmentation",
                "category": "model_evaluation",
                "status": "measured",
                "evidence_tier": temporal.get("label_quality_tier"),
                "scope": temporal.get("generalisation_scope"),
                "metrics": temporal.get("hard_metrics", {}),
                "headline_metrics": {
                    key: temporal.get("hard_metrics", {}).get(key)
                    for key in ("hard_dice", "hard_iou", "precision", "recall", "area_bias_percent")
                    if temporal.get("hard_metrics", {}).get(key) is not None
                },
                "claim_allowed": "one-AOI temporal silver-label performance",
                "claim_not_allowed": "independent expert accuracy",
                "artifacts": [_artifact(root, temporal_path)],
            }
        )
    else:
        tracks.append(
            {
                "id": "temporal_segmentation",
                "title": "Temporal glacier segmentation",
                "category": "model_evaluation",
                "status": "blocked_missing_artifact",
                "metrics": {},
                "artifacts": [_artifact(root, temporal_path)],
            }
        )

    if sentinel1:
        hard_metrics = sentinel1.get("hard_metrics", {})
        tracks.append(
            {
                "id": "sentinel1_multimodal_ablation",
                "title": "Sentinel-1 + Sentinel-2 multimodal ablation",
                "category": "model_evaluation",
                "status": "measured",
                "evidence_tier": sentinel1.get("label_quality_tier"),
                "scope": sentinel1.get("generalisation_scope"),
                "metrics": hard_metrics,
                "headline_metrics": {
                    key: hard_metrics.get(key)
                    for key in ("hard_dice", "hard_iou", "precision", "recall", "area_bias_percent")
                    if hard_metrics.get(key) is not None
                },
                "claim_allowed": "same-patch one-AOI multimodal feature-ablation result",
                "claim_not_allowed": "cross-region superiority or independent expert-label accuracy",
                "artifacts": [_artifact(root, sentinel1_path)],
            }
        )
    else:
        tracks.append(
            {
                "id": "sentinel1_multimodal_ablation",
                "title": "Sentinel-1 + Sentinel-2 multimodal ablation",
                "category": "model_evaluation",
                "status": "blocked_missing_artifact",
                "metrics": {},
                "headline_metrics": {},
                "artifacts": [_artifact(root, sentinel1_path)],
            }
        )

    if external:
        replay = external.get("external_replay", {})
        tracks.append(
            {
                "id": "external_transfer",
                "title": "Frozen cross-region transfer",
                "category": "model_evaluation",
                "status": "measured_provisional",
                "evidence_tier": "provisional_external_silver",
                "scope": "Ile Alatau calibration to untouched Zhetysu replay",
                "metrics": {
                    "n_external_glaciers": replay.get("n_glaciers"),
                    "baseline": replay.get("unconstrained_model_baseline"),
                    "candidate": replay.get("metrics_bootstrap"),
                    "paired_delta": replay.get("paired_delta_decoder_minus_unconstrained_model"),
                },
                "headline_metrics": {
                    "n_external_glaciers": replay.get("n_glaciers"),
                    "candidate_hard_dice": _estimate(replay.get("metrics_bootstrap", {}).get("hard_dice")),
                    "candidate_hard_iou": _estimate(replay.get("metrics_bootstrap", {}).get("hard_iou")),
                    "paired_dice_delta": _estimate(
                        replay.get("paired_delta_decoder_minus_unconstrained_model", {}).get("hard_dice")
                    ),
                },
                "claim_allowed": "frozen provisional external replay",
                "claim_not_allowed": "independent external accuracy",
                "artifacts": [_artifact(root, external_path)],
            }
        )
    else:
        tracks.append(
            {
                "id": "external_transfer",
                "title": "Frozen cross-region transfer",
                "category": "model_evaluation",
                "status": "blocked_missing_artifact",
                "metrics": {},
                "headline_metrics": {},
                "artifacts": [_artifact(root, external_path)],
            }
        )

    glavitu_path = "benchmarks/centralasia_glacierbench/current/glavitu_zhetysu_baseline.json"
    glavitu = _read_json(root / glavitu_path)
    glavitu_metrics = glavitu.get("metrics_bootstrap", {}) if glavitu else {}
    glavitu_global_path = "benchmarks/centralasia_glacierbench/current/glavitu_zhetysu_global_baseline.json"
    glavitu_global = _read_json(root / glavitu_global_path)
    glavitu_global_metrics = glavitu_global.get("metrics_bootstrap", {}) if glavitu_global else {}
    tracks.append(
        {
            "id": "glavitu_external_baseline",
            "title": "Official GlaViTU pretrained-model transfer",
            "category": "model_evaluation",
            "status": "measured_provisional" if glavitu else "data_ready_evaluation_pending",
            "evidence_tier": "external_pretrained_model_plus_provisional_silver_rgi",
            "scope": "frozen 2024 Zhetysu replay with no threshold tuning",
            "metrics": {
                "hma_finetuned": glavitu_metrics,
                "global": glavitu_global_metrics,
            },
            "headline_metrics": {
                "hma_hard_dice": _estimate(glavitu_metrics.get("hard_dice")),
                "hma_hard_iou": _estimate(glavitu_metrics.get("hard_iou")),
                "global_hard_dice": _estimate(glavitu_global_metrics.get("hard_dice")),
                "global_hard_iou": _estimate(glavitu_global_metrics.get("hard_iou")),
            },
            "claim_allowed": glavitu.get("claim_allowed") if glavitu else "external model artifacts ready",
            "claim_not_allowed": (
                glavitu.get("claim_not_allowed") if glavitu else "performance until the frozen replay is executed"
            ),
            "artifacts": [
                _artifact(root, glavitu_path),
                _artifact(root, glavitu_global_path),
            ],
        }
    )

    cryo_ready = _source_state(registry, "cryobench_gld") == "verified_local"
    cryo_result_path = "benchmarks/centralasia_glacierbench/current/cryobench_gld_baseline.json"
    cryo_result = _read_json(root / cryo_result_path)
    cryo_metrics = cryo_result.get("test_macro_bootstrap", {}) if cryo_result else {}
    tracks.append(
        {
            "id": "cryobench_lakes",
            "title": "Cryo-Bench external glacial-lake segmentation",
            "category": "model_evaluation",
            "status": (
                "measured_external_test"
                if cryo_result
                else "data_ready_evaluation_pending"
                if cryo_ready
                else "blocked_dataset_missing_or_unverified"
            ),
            "evidence_tier": "external_benchmark",
            "scope": "GLD frozen test split",
            "metrics": cryo_metrics,
            "headline_metrics": {
                key: _estimate(value)
                for key, value in cryo_metrics.items()
                if key in {"hard_dice_foreground", "hard_iou_foreground"}
            },
            "claim_allowed": (
                cryo_result.get("claim_allowed") if cryo_result else "dataset readiness" if cryo_ready else None
            ),
            "claim_not_allowed": (
                cryo_result.get("claim_not_allowed")
                if cryo_result
                else "lake segmentation performance until predictions are evaluated"
            ),
            "artifacts": [_artifact(root, cryo_result_path)],
        }
    )

    physical_sources = {
        source_id: _source_state(registry, source_id)
        for source_id in ("hugonnet_dhdt", "itslive_velocity", "oggm_rgi7")
    }
    independent_ready = all(
        physical_sources[source] in {"verified_local", "local_unverified"}
        for source in ("hugonnet_dhdt", "itslive_velocity")
    )
    itslive_metrics: dict[str, Any] = {}
    itslive_path = root / "data/external/centralasia_glacierbench/itslive/velocity_samples.parquet"
    if physical_sources["itslive_velocity"] == "verified_local":
        try:
            itslive_metrics = _itslive_metrics(itslive_path)
        except (OSError, ValueError, KeyError):
            itslive_metrics = {}
    hugonnet_metrics: dict[str, Any] = {}
    if independent_ready:
        try:
            hugonnet_metrics = build_hugonnet_reference_metrics(
                root
                / (
                    "data/external/centralasia_glacierbench/hugonnet/"
                    "hugonnet_2021_ds_rgi60_pergla_rates_10_20_worldwide_filled.hdf"
                ),
                itslive_metrics=itslive_metrics,
            )
        except (OSError, ValueError, KeyError, ImportError):
            hugonnet_metrics = {}
    tracks.append(
        {
            "id": "itslive_velocity_reference",
            "title": "Observed glacier motion from NASA ITS_LIVE",
            "category": "reference_evidence",
            "status": "measured_reference" if itslive_metrics else "blocked_velocity_samples_missing",
            "evidence_tier": "independent_physical_observation",
            "scope": "real point time series at large RGI7 glacier centroids across available Central Asia cubes",
            "metrics": itslive_metrics,
            "headline_metrics": itslive_metrics,
            "claim_allowed": "observed point-velocity context for the sampled glaciers" if itslive_metrics else None,
            "claim_not_allowed": "whole-glacier velocity, discharge or instability inference from a centroid point",
            "artifacts": [
                _artifact(
                    root,
                    "data/external/centralasia_glacierbench/itslive/velocity_samples.parquet",
                )
            ],
        }
    )
    tracks.append(
        {
            "id": "physical_consistency",
            "title": "Independent physical reference context",
            "category": "reference_evidence",
            "status": "measured_reference" if hugonnet_metrics else "blocked_physical_sources_missing",
            "evidence_tier": "independent_observation_plus_model_context",
            "scope": "Hugonnet RGI-13 mass change + sampled ITS_LIVE motion; no cross-inventory join",
            "source_states": physical_sources,
            "metrics": hugonnet_metrics,
            "headline_metrics": {
                key: hugonnet_metrics[key]
                for key in (
                    "glacier_records",
                    "area_weighted_mass_change_m_we_per_year",
                    "fraction_glaciers_with_negative_mass_change",
                    "itslive_sampled_glaciers",
                )
                if key in hugonnet_metrics
            },
            "claim_allowed": (
                "independent regional mass-change and sampled motion context" if hugonnet_metrics else None
            ),
            "claim_not_allowed": (
                "pixel-level validation, glacier-level thinning-motion correlation or causal instability inference"
            ),
            "artifacts": [
                _artifact(
                    root,
                    (
                        "data/external/centralasia_glacierbench/hugonnet/"
                        "hugonnet_2021_ds_rgi60_pergla_rates_10_20_worldwide_filled.hdf"
                    ),
                )
            ],
        }
    )

    hma_ready = _source_state(registry, "hma_lake_terminating_1990_2022") == "verified_local"
    event_ready = _source_state(registry, "hmaglofdb") in {"verified_local", "local_unverified"}
    hma_metrics: dict[str, Any] = {}
    event_metrics: dict[str, Any] = {}
    if hma_ready:
        try:
            hma_metrics = build_hma_reference_metrics(
                root / "data/external/centralasia_glacierbench/hma_ltg/HMA_LTG.gpkg"
            )
        except (OSError, ValueError, KeyError):
            hma_ready = False
    if hma_ready and event_ready:
        try:
            event_metrics = build_event_colocation_metrics(
                root / "data/external/centralasia_glacierbench/hma_ltg/HMA_LTG.gpkg",
                root / ("data/events/hmaglofdb/source/fidelsteiner-HMAGLOFDB-1d975de/Database/GLOFs/HMAGLOFDB.csv"),
            )
        except (OSError, ValueError, KeyError, ImportError):
            event_metrics = {}
    tracks.append(
        {
            "id": "hma_lake_terminating_reference",
            "title": "Observed lake-terminating glacier change, 1990-2022",
            "category": "reference_evidence",
            "status": "measured_reference" if hma_ready else "blocked_dataset_missing_or_invalid",
            "evidence_tier": "external_expert_validated_inventory",
            "scope": "Northern/Western Tien Shan, Central Tien Shan and Dzhungarsky Alatau",
            "metrics": hma_metrics,
            "headline_metrics": {
                key: hma_metrics[key]
                for key in (
                    "glacier_records_2022",
                    "aggregate_glacier_area_change_percent",
                    "lake_records_2022",
                    "aggregate_lake_area_change_percent",
                )
                if key in hma_metrics
            },
            "claim_allowed": "retrospective aggregate glacier-lake inventory change",
            "claim_not_allowed": "causal attribution, event probability or operational warning",
            "artifacts": [
                _artifact(
                    root,
                    "data/external/centralasia_glacierbench/hma_ltg/HMA_LTG.gpkg",
                )
            ],
        }
    )
    tracks.append(
        {
            "id": "cascade_risk",
            "title": "Retrospective glacier-event co-location",
            "category": "reference_evidence",
            "status": "measured_reference" if event_metrics else "blocked_event_or_lake_source",
            "evidence_tier": "expert_inventory_plus_observed_events",
            "scope": "HMA lake-terminating glacier geometry and HMAGLOFDB event coordinates",
            "metrics": event_metrics,
            "headline_metrics": {
                key: event_metrics[key]
                for key in (
                    "hma_glaciers_screened",
                    "events_in_regional_envelope",
                    "events_within_5km",
                    "unique_glaciers_with_event_within_5km",
                )
                if key in event_metrics
            },
            "claim_allowed": (
                "retrospective spatial event coverage and sensitivity screening" if event_metrics else None
            ),
            "claim_not_allowed": "operational GLOF probability or warning",
            "artifacts": [
                _artifact(
                    root,
                    ("data/events/hmaglofdb/source/fidelsteiner-HMAGLOFDB-1d975de/Database/GLOFs/HMAGLOFDB.csv"),
                ),
                _artifact(
                    root,
                    "data/external/centralasia_glacierbench/hma_ltg/HMA_LTG.gpkg",
                ),
            ],
        }
    )

    active_evidence = build_active_evidence_readiness(root)
    tracks.append(
        {
            "id": "active_evidence_acquisition",
            "title": "Retrospective active evidence acquisition",
            "category": "decision_support_evaluation",
            "status": active_evidence["status"],
            "evidence_tier": "source_reviewed_event_replay_required",
            "scope": "pre-event snapshots, verified controls and realised decision-loss reduction",
            "metrics": active_evidence["counts"],
            "headline_metrics": active_evidence["counts"],
            "blockers": active_evidence["blockers"],
            "claim_allowed": active_evidence["claim_allowed"],
            "claim_not_allowed": active_evidence["claim_not_allowed"],
            "artifacts": active_evidence["artifacts"],
        }
    )

    return {
        "schema": "centralasia-glacierbench.report.v2",
        "benchmark_version": "0.4.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_name": "CentralAsia-GlacierBench",
        "policy": {
            "no_composite_score": True,
            "no_synthetic_metrics": True,
            "frozen_test_splits": True,
            "glacier_is_sampling_unit": True,
            "model_outputs_are_separate_from_observations": True,
        },
        "sources": registry,
        "tracks": tracks,
        "summary": {
            "sources_total": len(registry),
            "sources_local": sum(bool(row["available"]) for row in registry),
            "sources_verified": sum(row["state"] == "verified_local" for row in registry),
            "sources_metadata_only": sum(row["state"] == "metadata_only" for row in registry),
            "sources_missing": sum(row["state"] == "missing" for row in registry),
            "tracks_total": len(tracks),
            "tracks_data_ready": sum(track["status"] == "data_ready_evaluation_pending" for track in tracks),
            "tracks_blocked": sum(str(track["status"]).startswith("blocked") for track in tracks),
            "model_evaluations_total": sum(track["category"] == "model_evaluation" for track in tracks),
            "model_evaluations_measured": sum(
                track["category"] == "model_evaluation" and str(track["status"]).startswith("measured")
                for track in tracks
            ),
            "reference_evidence_total": sum(track["category"] == "reference_evidence" for track in tracks),
            "reference_evidence_available": sum(
                track["category"] == "reference_evidence" and str(track["status"]).startswith("measured")
                for track in tracks
            ),
            "decision_support_evaluations_total": sum(
                track["category"] == "decision_support_evaluation" for track in tracks
            ),
            "decision_support_evaluations_ready": sum(
                track["category"] == "decision_support_evaluation" and track["status"] == "evaluation_ready"
                for track in tracks
            ),
        },
        "claims_not_unlocked": [
            "independent expert gold-label accuracy",
            "operational GLOF warning or calibrated event probability",
            "field-validated glacier volume or runoff forecast",
        ],
    }
