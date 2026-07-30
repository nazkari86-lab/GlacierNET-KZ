"""Physics-constrained decoding for glacier-inventory update workflows.

This module deliberately treats an inventory outline as a search prior, not as
current ground truth.  It suppresses physically implausible, disconnected snow
predictions while retaining an explicit claim boundary: results cannot be used
as independent validation against the same inventory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class InventoryGuidedDecoderConfig:
    """Frozen parameters for inventory-guided spectral decoding."""

    ndsi_threshold: float = 0.5
    support_buffer_m: float = 100.0
    retain_inventory_connected_components: bool = True

    def __post_init__(self) -> None:
        if not -1.0 <= self.ndsi_threshold <= 1.0:
            raise ValueError("ndsi_threshold must be between -1 and 1")
        if self.support_buffer_m < 0:
            raise ValueError("support_buffer_m must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalized_difference(green: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """Return finite NDSI values from equally shaped green and SWIR arrays."""
    green_array = np.asarray(green, dtype=np.float32)
    swir_array = np.asarray(swir, dtype=np.float32)
    if green_array.shape != swir_array.shape:
        raise ValueError("green and swir arrays must have identical shapes")
    denominator = green_array + swir_array
    return np.divide(
        green_array - swir_array,
        denominator,
        out=np.zeros_like(green_array),
        where=np.abs(denominator) > 1e-8,
    )


def inventory_support_mask(
    inventory_mask: np.ndarray,
    *,
    pixel_size_m: float,
    buffer_m: float,
) -> np.ndarray:
    """Expand an inventory search prior by a physical-distance buffer."""
    inventory = np.asarray(inventory_mask, dtype=bool)
    if inventory.ndim != 2:
        raise ValueError("inventory_mask must be two-dimensional")
    if not inventory.any():
        raise ValueError("inventory_mask must contain at least one inventory pixel")
    if pixel_size_m <= 0:
        raise ValueError("pixel_size_m must be positive")
    if buffer_m < 0:
        raise ValueError("buffer_m must be non-negative")
    distance_m = ndimage.distance_transform_edt(~inventory) * float(pixel_size_m)
    return distance_m <= float(buffer_m)


def retain_seeded_components(mask: np.ndarray, seed_mask: np.ndarray) -> np.ndarray:
    """Keep candidate components that intersect the historical inventory."""
    candidate = np.asarray(mask, dtype=bool)
    seed = np.asarray(seed_mask, dtype=bool)
    if candidate.shape != seed.shape:
        raise ValueError("mask and seed_mask must have identical shapes")
    labels, _ = ndimage.label(candidate)
    component_ids = np.unique(labels[seed])
    component_ids = component_ids[component_ids > 0]
    if not len(component_ids):
        return np.zeros_like(candidate)
    return np.isin(labels, component_ids)


def inventory_guided_decode(
    ndsi: np.ndarray,
    inventory_mask: np.ndarray,
    *,
    pixel_size_m: float,
    config: InventoryGuidedDecoderConfig | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Decode current spectral evidence inside a declared inventory search area.

    The returned diagnostics make the circularity risk machine-readable.  The
    output is suitable for candidate-boundary screening and annotation
    prioritisation, not accuracy validation against ``inventory_mask``.
    """
    settings = config or InventoryGuidedDecoderConfig()
    ndsi_array = np.asarray(ndsi, dtype=np.float32)
    inventory = np.asarray(inventory_mask, dtype=bool)
    if ndsi_array.shape != inventory.shape or ndsi_array.ndim != 2:
        raise ValueError("ndsi and inventory_mask must be equally shaped 2D arrays")

    support = inventory_support_mask(
        inventory,
        pixel_size_m=pixel_size_m,
        buffer_m=settings.support_buffer_m,
    )
    spectral_candidate = np.isfinite(ndsi_array) & (ndsi_array >= settings.ndsi_threshold)
    decoded = spectral_candidate & support
    if settings.retain_inventory_connected_components:
        decoded = retain_seeded_components(decoded, inventory)

    inventory_pixels = int(inventory.sum())
    predicted_pixels = int(decoded.sum())
    diagnostics = {
        "schema": "glaciernet-kz.inventory-guided-decoder.v1",
        "config": settings.to_dict(),
        "inventory_pixels": inventory_pixels,
        "support_pixels": int(support.sum()),
        "predicted_pixels": predicted_pixels,
        "predicted_to_inventory_area_ratio": predicted_pixels / inventory_pixels,
        "spectral_support_fraction": float(spectral_candidate[support].mean()),
        "inventory_spectral_fraction": float(spectral_candidate[inventory].mean()),
        "claim_tier": "inventory_guided_screening",
        "circular_validation_warning": (
            "The inventory is a decoding prior and cannot also serve as independent accuracy ground truth."
        ),
    }
    return decoded.astype(np.uint8), diagnostics
