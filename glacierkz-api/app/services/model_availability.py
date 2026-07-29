"""Check which ML models are complete and trusted enough for inference."""

from __future__ import annotations

from pathlib import Path

import src.config as core_config
from src.model_registry import MODEL_SPECS, model_metadata
from src.model_security import verify_trusted_model

WEIGHTS_MAP: dict[str, str] = {
    "unet": "unet_best.h5",
    "attention_unet": "attention_unet_best.h5",
    "unet_plus_plus": "unet_plus_plus_best.h5",
    "rf": "random_forest.pkl",
}


def weights_path(model_name: str) -> Path | None:
    spec = MODEL_SPECS.get(model_name)
    if spec is not None and spec.artifact is not None:
        return spec.artifact_path(core_config.PROJECT_ROOT)
    filename = WEIGHTS_MAP.get(model_name)
    if filename is None:
        return None
    return core_config.MODELS_DIR / filename


def is_model_available(model_name: str) -> bool:
    if model_name == "ndsi":
        return True
    if model_name == "ensemble":
        return is_model_available("unet")
    path = weights_path(model_name)
    if path is None or not path.exists():
        return False
    spec = MODEL_SPECS.get(model_name)
    if spec is None:
        return True
    report = spec.report_path(core_config.PROJECT_ROOT)
    if spec.evidence_tier != "legacy" and (report is None or not report.is_file()):
        return False
    try:
        verify_trusted_model(path, root=core_config.PROJECT_ROOT)
        if spec.evidence_tier != "legacy":
            spec.calibrated_threshold(core_config.PROJECT_ROOT)
    except (FileNotFoundError, OSError, ValueError, KeyError):
        return False
    return True


def filter_available_models(catalog: list[dict]) -> list[dict]:
    """Return catalog entries that can run inference right now."""
    available = []
    for entry in catalog:
        if is_model_available(entry["name"]):
            spec = MODEL_SPECS.get(entry["name"])
            metadata = model_metadata(spec) if spec is not None else {}
            available.append({**entry, **metadata, "available": True})
    return available
