"""Check which ML models have trained weights on disk."""

from __future__ import annotations

from pathlib import Path

import src.config as core_config

WEIGHTS_MAP: dict[str, str] = {
    "unet": "unet_best.h5",
    "attention_unet": "attention_unet_best.h5",
    "unet_plus_plus": "unet_plus_plus_best.h5",
    "rf": "random_forest.pkl",
}


def weights_path(model_name: str) -> Path | None:
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
    return path is not None and path.exists()


def filter_available_models(catalog: list[dict]) -> list[dict]:
    """Return catalog entries that can run inference right now."""
    available = []
    for entry in catalog:
        if is_model_available(entry["name"]):
            available.append({**entry, "available": True})
    return available
