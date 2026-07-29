from __future__ import annotations

import numpy as np

from scripts.build_enhanced_annotation_pack import annual_evidence, remove_small_components


def test_remove_small_components_keeps_only_supported_regions() -> None:
    mask = np.zeros((12, 12), dtype=bool)
    mask[1, 1] = True
    mask[5:8, 5:8] = True
    cleaned = remove_small_components(mask, minimum_pixels=5)
    assert not cleaned[1, 1]
    assert cleaned[5:8, 5:8].all()


def test_annual_evidence_rejects_unconnected_outer_snow() -> None:
    shape = (32, 32)
    rgi = np.zeros(shape, dtype=bool)
    rgi[10:22, 10:22] = True
    zone = np.ones(shape, dtype=bool)
    ndsi = np.zeros(shape, dtype=np.float32)
    ndsi[11:21, 11:21] = 0.8
    ndsi[1:5, 1:5] = 0.9
    green = np.full(shape, 0.2, dtype=np.float32)
    temporal = np.zeros(shape, dtype=np.float32)
    temporal[11:21, 11:21] = 1.0
    temporal[1:5, 1:5] = 1.0
    label, review, score = annual_evidence(
        ndsi=ndsi,
        green=green,
        valid=np.ones(shape, dtype=bool),
        temporal_clean_fraction=temporal,
        rgi_mask=rgi,
        target_zone=zone,
        pixel_size_m=10.0,
    )
    assert label[12:20, 12:20].all()
    assert not label[1:5, 1:5].any()
    assert review.any()
    assert score.shape == shape
