"""Single source of truth for deployable GlacierNET-KZ segmentation models.

Research artifacts are only exposed to runtime inference when the artifact,
evaluation report, feature order, and validation-calibrated threshold are all
explicit.  This prevents silently running a model with the wrong band order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import config

TERRAIN_FEATURES = (
    "elevation_m_normalized",
    "slope_degrees_normalized",
    "aspect_degrees_normalized",
)
SENTINEL1_FEATURES = ("VV_dB_normalized", "VH_dB_normalized")


@dataclass(frozen=True)
class ModelSpec:
    name: str
    display_name: str
    description: str
    artifact: str | None
    report: str | None
    feature_schema: tuple[str, ...]
    default_threshold: float = 0.5
    supports_tta: bool = False
    supports_crf: bool = False
    supports_uncertainty: bool = False
    evidence_tier: str = "baseline"
    recommended: bool = False
    year_min: int | None = None
    year_max: int | None = None

    @property
    def channel_count(self) -> int:
        return len(self.feature_schema)

    def artifact_path(self, root: Path = config.PROJECT_ROOT) -> Path | None:
        return root / self.artifact if self.artifact else None

    def report_path(self, root: Path = config.PROJECT_ROOT) -> Path | None:
        return root / self.report if self.report else None

    def calibrated_threshold(self, root: Path = config.PROJECT_ROOT) -> float:
        path = self.report_path(root)
        if path is None or not path.is_file():
            return self.default_threshold
        payload = json.loads(path.read_text(encoding="utf-8"))
        threshold = payload.get("threshold_calibration", {}).get("selected_threshold")
        if threshold is None:
            return self.default_threshold
        value = float(threshold)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Invalid calibrated threshold for {self.name}: {value}")
        return value


LEGACY_SCHEMA = tuple(config.ALL_BAND_NAMES)
S2_TERRAIN_SCHEMA = LEGACY_SCHEMA + TERRAIN_FEATURES
S2_TERRAIN_S1_SCHEMA = S2_TERRAIN_SCHEMA + SENTINEL1_FEATURES

MODEL_SPECS: dict[str, ModelSpec] = {
    "temporal_s2_terrain_s1": ModelSpec(
        name="temporal_s2_terrain_s1",
        display_name="Multimodal U-Net · S2 + terrain + SAR",
        description=(
            "Best measured local model: Sentinel-2, spectral indices, terrain and "
            "Sentinel-1 VV/VH. Validation-calibrated threshold; 2024 temporal holdout."
        ),
        artifact="models/unet_best_sentinel2_terrain_s1_year_holdout_2017_2024",
        report="results/ablation_unet_sentinel2_terrain_s1_2017_2024.json",
        feature_schema=S2_TERRAIN_S1_SCHEMA,
        supports_tta=True,
        supports_uncertainty=True,
        evidence_tier="silver_temporal_holdout",
        recommended=True,
        year_min=2017,
        year_max=2024,
    ),
    "temporal_s2_terrain": ModelSpec(
        name="temporal_s2_terrain",
        display_name="Temporal U-Net · S2 + terrain",
        description=(
            "Broader 2016–2024 temporal model using Sentinel-2, spectral indices "
            "and terrain; does not require Sentinel-1."
        ),
        artifact="models/unet_best_sentinel2_terrain_year_holdout_2016_2024",
        report="results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json",
        feature_schema=S2_TERRAIN_SCHEMA,
        supports_tta=True,
        supports_uncertainty=True,
        evidence_tier="silver_temporal_holdout",
        year_min=2016,
        year_max=2024,
    ),
    "unet": ModelSpec(
        name="unet",
        display_name="Legacy U-Net · S2",
        description="Legacy 11-channel U-Net retained for reproducibility.",
        artifact="models/unet_best.h5",
        report=None,
        feature_schema=LEGACY_SCHEMA,
        supports_tta=True,
        supports_crf=True,
        supports_uncertainty=True,
        evidence_tier="legacy",
    ),
    "attention_unet": ModelSpec(
        name="attention_unet",
        display_name="Legacy Attention U-Net · S2",
        description="Legacy attention model retained for reproducibility.",
        artifact="models/attention_unet_best.h5",
        report=None,
        feature_schema=LEGACY_SCHEMA,
        supports_tta=True,
        supports_crf=True,
        supports_uncertainty=True,
        evidence_tier="legacy",
    ),
    "unet_plus_plus": ModelSpec(
        name="unet_plus_plus",
        display_name="Legacy U-Net++ · S2",
        description="Legacy nested U-Net retained for reproducibility.",
        artifact="models/unet_plus_plus_best.h5",
        report=None,
        feature_schema=LEGACY_SCHEMA,
        supports_tta=True,
        supports_crf=True,
        supports_uncertainty=True,
        evidence_tier="legacy",
    ),
}


def get_model_spec(name: str) -> ModelSpec:
    try:
        return MODEL_SPECS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown segmentation model: {name}") from exc


def model_metadata(spec: ModelSpec, root: Path = config.PROJECT_ROOT) -> dict[str, object]:
    return {
        "name": spec.name,
        "display_name": spec.display_name,
        "description": spec.description,
        "supports_tta": spec.supports_tta,
        "supports_crf": spec.supports_crf,
        "supports_uncertainty": spec.supports_uncertainty,
        "channel_count": spec.channel_count,
        "feature_schema": list(spec.feature_schema),
        "decision_threshold": spec.calibrated_threshold(root),
        "evidence_tier": spec.evidence_tier,
        "recommended": spec.recommended,
        "year_range": [spec.year_min, spec.year_max] if spec.year_min is not None else None,
    }
