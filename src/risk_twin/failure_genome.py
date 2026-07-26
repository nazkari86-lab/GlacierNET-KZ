"""Explainable screening taxonomy for model-defined failure pathways."""

from __future__ import annotations

from typing import Any

GENOME_RULES: dict[str, set[str]] = {
    "filling_overtopping_erosion": {
        "rainfall_mm_24h",
        "temperature_anomaly_c",
        "snowmelt_index",
        "water_level_rise_m",
    },
    "outlet_degradation": {
        "outlet_blockage_fraction",
        "outlet_capacity_loss_fraction",
        "freeboard_loss_m",
    },
    "slope_impact_wave": {
        "slope_failure_volume_m3",
        "slope_deformation_impulse",
    },
    "glacier_collapse_wave": {
        "ice_avalanche_volume_m3",
        "glacier_velocity_impulse",
    },
}


def classify_failure_genome(stresses: dict[str, float]) -> dict[str, Any]:
    if not stresses:
        return {
            "dominant": None,
            "alternatives": [],
            "status": "insufficient_stress_definition",
            "interpretation": "screening taxonomy, not a diagnosed failure mechanism",
        }
    scores = []
    positive = {name for name, value in stresses.items() if value > 0}
    for genome, variables in GENOME_RULES.items():
        matched = sorted(positive & variables)
        scores.append(
            {
                "genome": genome,
                "matched_variables": matched,
                "coverage": len(matched) / len(variables),
            }
        )
    ranked = sorted(scores, key=lambda row: (-row["coverage"], row["genome"]))
    dominant = ranked[0] if ranked and ranked[0]["coverage"] > 0 else None
    alternatives = [row for row in ranked[1:] if row["coverage"] > 0]
    return {
        "dominant": dominant,
        "alternatives": alternatives,
        "status": "screening_taxonomy" if dominant else "unclassified",
        "interpretation": "rule-based Failure Genome hypothesis for review, not a diagnosed mechanism",
    }
