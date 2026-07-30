"""Cohort-level scientific validity checks."""

from __future__ import annotations

from collections.abc import Iterable

from .schemas import GlacierFeatureRecord


def validate_pre_outcome_features(
    record: GlacierFeatureRecord,
    required_features: Iterable[str] = (),
) -> None:
    """Fail closed when matching data are missing or observed after the anchor.

    Matching is only defensible when every feature was available by the
    declared anchor.  The outcome is deliberately not inspected here because
    it is never part of the matching vector.
    """

    missing = sorted(set(required_features).difference(record.features))
    if missing:
        raise ValueError("missing required pre-outcome features: " + ", ".join(missing))

    leaked = sorted(
        feature_name
        for feature_name, feature in record.features.items()
        if feature.observed_at.year > record.anchor_year
    )
    if leaked:
        raise ValueError("features observed after anchor_year: " + ", ".join(leaked))
