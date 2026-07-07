"""Verify trained model weights on disk."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import config

MODELS = {
    "unet": "unet_best.h5",
    "attention_unet": "attention_unet_best.h5",
    "unet_plus_plus": "unet_plus_plus_best.h5",
    "random_forest": "random_forest.pkl",
}


@pytest.mark.parametrize("name,filename", list(MODELS.items()))
def test_production_model_weights(name: str, filename: str):
    path = config.MODELS_DIR / filename
    if name == "unet_plus_plus" and not path.exists():
        pytest.skip(
            "U-Net++ weights missing. Train with: python scripts/train_unet_plus_plus.py --year 2020"
        )
    assert path.is_file(), f"Missing weights for {name}: {path}"
    assert path.stat().st_size > 100_000, f"Weights file too small: {path}"
