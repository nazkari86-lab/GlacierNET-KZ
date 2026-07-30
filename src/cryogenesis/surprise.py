"""Conservative Release 1 surprise classification."""

from __future__ import annotations

from .schemas import MatchStatus, SurpriseClass


def classify_surprise(
    *,
    match_status: MatchStatus,
    target_outcome: float | None,
    raw_divergence: float | None,
    comparator_interval: tuple[float, float] | None,
    measurement_uncertainty: float | None,
) -> SurpriseClass:
    """Classify a retrospective difference, abstaining before interpretation."""

    if match_status != "matched":
        return "comparison_inconclusive"
    if target_outcome is None or raw_divergence is None or comparator_interval is None:
        return "comparison_inconclusive"
    if measurement_uncertainty is not None:
        if measurement_uncertainty < 0:
            raise ValueError("measurement_uncertainty must be non-negative")
        if abs(raw_divergence) <= measurement_uncertainty:
            return "observation_inconclusive"
    if comparator_interval[0] <= target_outcome <= comparator_interval[1]:
        return "trajectory_consistent"
    return "unexplained_divergence_candidate"
