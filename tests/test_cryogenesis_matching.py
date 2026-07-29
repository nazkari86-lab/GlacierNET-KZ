from datetime import datetime, timezone

import pytest

from src.cryogenesis.cohort import validate_pre_outcome_features
from src.cryogenesis.matching import MatchConfig, match_twins
from src.cryogenesis.schemas import FeatureValue, GlacierFeatureRecord


def fv(value: float, year: int, unit: str = "unitless") -> FeatureValue:
    return FeatureValue(
        value,
        unit,
        datetime(year, 7, 1, tzinfo=timezone.utc),
        "fixture",
        "observed",
    )


def record(
    rgi_id: str,
    area: float,
    elevation: float,
    outcome: float,
    split: str = "development",
) -> GlacierFeatureRecord:
    return GlacierFeatureRecord(
        rgi_id=rgi_id,
        basin_id="B1",
        region_id="R1",
        split=split,
        anchor_year=2020,
        outcome_year=2024,
        features={
            "area_km2": fv(area, 2020, "km2"),
            "elevation_m": fv(elevation, 2020, "m"),
        },
        outcome=fv(outcome, 2024, "fraction"),
    )


def test_post_anchor_feature_is_rejected():
    target = record("A", 2.0, 3500, -0.1)
    leaked = dict(target.features)
    leaked["future_velocity"] = fv(10, 2024, "m/year")
    with pytest.raises(ValueError, match="future_velocity"):
        validate_pre_outcome_features(
            target.__class__(**{**target.__dict__, "features": leaked})
        )


def test_matching_is_deterministic_and_never_matches_self():
    rows = [
        record("A", 2.0, 3500, -0.10),
        record("B", 2.1, 3510, -0.08),
        record("C", 1.9, 3490, -0.12),
        record("D", 2.2, 3530, -0.09),
    ]
    result = match_twins(
        rows[0],
        rows,
        MatchConfig(feature_weights={"area_km2": 1, "elevation_m": 1}),
    )
    assert result.status == "matched"
    assert [item.rgi_id for item in result.twins] == ["B", "C", "D"]
    assert sum(item.weight for item in result.twins) == pytest.approx(1)


def test_outcome_changes_do_not_change_selected_twins():
    rows = [
        record("A", 2.0, 3500, -0.10),
        record("B", 2.1, 3510, -0.08),
        record("C", 1.9, 3490, -0.12),
        record("D", 2.2, 3530, -0.09),
    ]
    config = MatchConfig(
        feature_weights={"area_km2": 1, "elevation_m": 1}
    )
    first = match_twins(rows[0], rows, config)
    changed = [
        rows[0],
        *(
            row.__class__(
                **{**row.__dict__, "outcome": fv(99, 2024)}
            )
            for row in rows[1:]
        ),
    ]
    second = match_twins(changed[0], changed, config)
    assert [item.rgi_id for item in first.twins] == [
        item.rgi_id for item in second.twins
    ]
