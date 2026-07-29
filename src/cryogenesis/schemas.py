"""Immutable evidence records for CryoGenesis Release 1.

The scientific core passes these records between stages so that provenance,
matching decisions, and claim boundaries remain explicit and serialisable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

QualityState = Literal[
    "observed",
    "not_observed",
    "not_applicable",
    "context_only",
]
Split = Literal[
    "development",
    "temporal_test",
    "spatial_test",
    "external_test",
]
MatchStatus = Literal["matched", "limited_match", "no_valid_counterfactual"]
SurpriseClass = Literal[
    "observation_inconclusive",
    "comparison_inconclusive",
    "trajectory_consistent",
    "unexplained_divergence_candidate",
]

_QUALITY_STATES = {
    "observed",
    "not_observed",
    "not_applicable",
    "context_only",
}
_SPLITS = {"development", "temporal_test", "spatial_test", "external_test"}
_MATCH_STATUSES = {"matched", "limited_match", "no_valid_counterfactual"}
_SURPRISE_CLASSES = {
    "observation_inconclusive",
    "comparison_inconclusive",
    "trajectory_consistent",
    "unexplained_divergence_candidate",
}


@dataclass(frozen=True)
class SourceAsset:
    """A content-addressed local input used to construct evidence."""

    source_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.sha256
        ):
            raise ValueError(
                "sha256 must be a lowercase 64-character hexadecimal digest"
            )
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")


@dataclass(frozen=True)
class FeatureValue:
    """A typed value together with its observation time and provenance."""

    value: float | int | str | None
    unit: str
    observed_at: datetime
    source_id: str
    quality_state: QualityState
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.quality_state not in _QUALITY_STATES:
            raise ValueError(f"unsupported quality_state: {self.quality_state}")
        if self.uncertainty is not None and self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")


@dataclass(frozen=True)
class GlacierFeatureRecord:
    """Pre-outcome glacier features and one retrospective mapped outcome."""

    rgi_id: str
    basin_id: str
    region_id: str
    split: Split
    anchor_year: int
    outcome_year: int
    features: dict[str, FeatureValue]
    outcome: FeatureValue | None

    def __post_init__(self) -> None:
        if self.split not in _SPLITS:
            raise ValueError(f"unsupported split: {self.split}")
        if self.outcome_year <= self.anchor_year:
            raise ValueError("outcome_year must be later than anchor_year")


@dataclass(frozen=True)
class TwinMatch:
    """One comparator and its auditable contribution to the twin estimate."""

    rgi_id: str
    total_distance: float
    component_distances: dict[str, float]
    weight: float


@dataclass(frozen=True)
class MatchResult:
    """Complete matching decision, including abstention evidence."""

    target_rgi_id: str
    status: MatchStatus
    twins: tuple[TwinMatch, ...]
    rejection_reasons: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in _MATCH_STATUSES:
            raise ValueError(f"unsupported match status: {self.status}")


@dataclass(frozen=True)
class DivergenceResult:
    """Bounded retrospective difference between target and comparators."""

    target_outcome: float
    comparator_outcome: float
    raw_divergence: float
    standardized_divergence: float | None
    comparator_interval: tuple[float, float]
    leave_one_out_range: tuple[float, float]


@dataclass(frozen=True)
class DiscoveryPassport:
    """Immutable, content-addressed public evidence for one glacier."""

    schema: str
    cohort_id: str
    target_rgi_id: str
    claim_tier: str
    match: MatchResult
    divergence: DivergenceResult | None
    surprise_class: SurpriseClass
    claims_allowed: tuple[str, ...]
    claims_not_allowed: tuple[str, ...]
    provenance: tuple[SourceAsset, ...]
    payload_sha256: str = ""

    def __post_init__(self) -> None:
        if self.surprise_class not in _SURPRISE_CLASSES:
            raise ValueError(f"unsupported surprise class: {self.surprise_class}")
        if self.payload_sha256 and (
            len(self.payload_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.payload_sha256
            )
        ):
            raise ValueError(
                "payload_sha256 must be empty or a lowercase "
                "64-character hexadecimal digest"
            )


@dataclass(frozen=True)
class VerificationResult:
    """Result returned by a saved-passport integrity check."""

    valid: bool
    errors: tuple[str, ...] = ()

