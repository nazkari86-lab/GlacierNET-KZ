from __future__ import annotations

import numpy as np
import pytest

from src.inventory_guided_decoding import (
    InventoryGuidedDecoderConfig,
    inventory_guided_decode,
    inventory_support_mask,
    normalized_difference,
    retain_seeded_components,
)


def test_normalized_difference_is_finite_at_zero_denominator() -> None:
    result = normalized_difference(np.array([[0.6, 0.0]]), np.array([[0.2, 0.0]]))
    assert np.allclose(result, [[0.5, 0.0]])


def test_inventory_support_uses_physical_buffer() -> None:
    inventory = np.zeros((7, 7), dtype=bool)
    inventory[3, 3] = True
    support = inventory_support_mask(inventory, pixel_size_m=10, buffer_m=10)
    assert int(support.sum()) == 5
    assert support[3, 3]
    assert not support[1, 3]


def test_seeded_components_remove_disconnected_snow() -> None:
    candidate = np.zeros((6, 6), dtype=bool)
    candidate[1:3, 1:3] = True
    candidate[4:6, 4:6] = True
    seed = np.zeros_like(candidate)
    seed[1, 1] = True
    retained = retain_seeded_components(candidate, seed)
    assert retained[1:3, 1:3].all()
    assert not retained[4:6, 4:6].any()


def test_decoder_is_fail_closed_and_reports_circularity() -> None:
    inventory = np.zeros((9, 9), dtype=bool)
    inventory[3:6, 3:6] = True
    ndsi = np.full((9, 9), -0.2, dtype=np.float32)
    ndsi[4, 4] = 0.8
    ndsi[0, 0] = 0.9
    mask, diagnostics = inventory_guided_decode(
        ndsi,
        inventory,
        pixel_size_m=10,
        config=InventoryGuidedDecoderConfig(ndsi_threshold=0.4, support_buffer_m=20),
    )
    assert int(mask.sum()) == 1
    assert mask[4, 4] == 1
    assert mask[0, 0] == 0
    assert diagnostics["claim_tier"] == "inventory_guided_screening"
    assert "cannot also serve" in diagnostics["circular_validation_warning"]


def test_invalid_config_is_rejected() -> None:
    with pytest.raises(ValueError, match="ndsi_threshold"):
        InventoryGuidedDecoderConfig(ndsi_threshold=2)
