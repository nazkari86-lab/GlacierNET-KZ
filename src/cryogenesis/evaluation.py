"""Aggregate, descriptive Release 1 cohort diagnostics."""

from __future__ import annotations

from collections import Counter

from .schemas import DiscoveryPassport


def cohort_report(
    passports: list[DiscoveryPassport],
    excluded_count: int = 0,
) -> dict[str, object]:
    statuses = Counter(passport.match.status for passport in passports)
    surprises = Counter(passport.surprise_class for passport in passports)
    return {
        "passport_count": len(passports),
        "excluded_count": excluded_count,
        "match_status_counts": dict(sorted(statuses.items())),
        "surprise_class_counts": dict(sorted(surprises.items())),
        "passport_verifier_target_rate": 1.0 if passports else 0.0,
    }
