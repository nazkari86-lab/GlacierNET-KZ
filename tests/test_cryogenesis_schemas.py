from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from src.cryogenesis.schemas import (
    FeatureValue,
    GlacierFeatureRecord,
    SourceAsset,
)


def test_feature_values_are_typed_timestamped_and_immutable():
    value = FeatureValue(
        value=2.5,
        unit="km2",
        observed_at=datetime(2020, 8, 1, tzinfo=timezone.utc),
        source_id="rgi",
        quality_state="observed",
    )
    assert value.value == 2.5
    with pytest.raises(FrozenInstanceError):
        value.value = 3.0


def test_feature_record_rejects_outcome_before_anchor():
    with pytest.raises(ValueError, match="outcome_year"):
        GlacierFeatureRecord(
            rgi_id="RGI-A",
            basin_id="B1",
            region_id="R1",
            split="development",
            anchor_year=2024,
            outcome_year=2020,
            features={},
            outcome=None,
        )


def test_source_asset_requires_a_sha256_digest():
    with pytest.raises(ValueError, match="sha256"):
        SourceAsset(
            source_id="rgi",
            relative_path="data/rgi/rgi.shp",
            sha256="bad",
            size_bytes=10,
        )
