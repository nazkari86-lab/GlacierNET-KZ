from __future__ import annotations

import pandas as pd

from scripts.evaluate_provisional_zhetysu_external import (
    RAW_DIR,
    ZHETYSU_CANDIDATE_BBOX,
    _is_candidate,
    _validate_raster,
)


def test_candidate_filter_is_explicit_and_reproducible() -> None:
    frame = pd.DataFrame({"cenlon": [78.9, 80.0, 84.2], "cenlat": [44.0, 44.0, 44.0]})
    assert len(_is_candidate(frame)) == 1
    assert ZHETYSU_CANDIDATE_BBOX == (79.0, 43.0, 84.1, 45.37)


def test_committed_external_raster_has_frozen_spatial_contract() -> None:
    raster = next(RAW_DIR.glob("*.tif"))
    metadata = _validate_raster(raster)
    assert metadata["bands"] == 10
    assert metadata["crs"] == "EPSG:32645"
    assert metadata["pixel_size_m"] == [10.0, 10.0]
    assert metadata["bytes"] > 0
