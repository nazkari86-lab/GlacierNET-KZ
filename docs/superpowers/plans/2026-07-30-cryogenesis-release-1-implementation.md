# CryoGenesis X Release 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a leakage-safe, physical-data Counterfactual Twin Bank that emits validated Discovery Passports and exposes them through a read-only API and `/discovery` workspace.

**Architecture:** A new dependency-light `src/cryogenesis` scientific core reads versioned local source records, freezes pre-outcome features, matches comparable glaciers with an auditable distance, measures retrospective mapped-area divergence, and writes immutable JSON passports. The FastAPI and Next.js layers only read validated saved artefacts; they never recalculate science or substitute synthetic objects.

**Tech Stack:** Python 3.10, dataclasses, NumPy, pandas, GeoPandas, Rasterio, xarray/netCDF4, FastAPI/Pydantic, pytest, Next.js 16, React 19, TypeScript, Leaflet, Vitest, Playwright.

---

## Scope

This plan implements Release 1 from
`docs/superpowers/specs/2026-07-30-cryogenesis-counterfactual-twin-design.md`.
It does not score physical mechanisms, calculate active information gain,
identify causal effects, update Risk Twin scores, or claim prospective
forecasting.

## File structure

### Scientific core

- Create `src/cryogenesis/__init__.py` — public Release 1 API.
- Create `src/cryogenesis/schemas.py` — immutable typed records and enum-like statuses.
- Create `src/cryogenesis/source_registry.py` — registered local source resolution, hashes and timestamp checks.
- Create `src/cryogenesis/features.py` — RGI, terrain, climate, annual mapped-area and observation-quality features.
- Create `src/cryogenesis/cohort.py` — eligibility, split and manifest construction.
- Create `src/cryogenesis/matching.py` — calipers, auditable distance and deterministic twin selection.
- Create `src/cryogenesis/divergence.py` — comparator outcome, intervals and sensitivity.
- Create `src/cryogenesis/surprise.py` — bounded Release 1 surprise classification.
- Create `src/cryogenesis/mechanisms.py` — fixed catalogue validation only.
- Create `src/cryogenesis/passport.py` — immutable passport assembly, hashing and verification.
- Create `src/cryogenesis/evaluation.py` — aggregate matching and abstention metrics.

### Commands, protocols and artefacts

- Create `scripts/build_cryogenesis_cohort.py`.
- Create `scripts/validate_cryogenesis_passports.py`.
- Create `benchmarks/cryogenesis/protocol.md`.
- Create `benchmarks/cryogenesis/feature_schema.json`.
- Create `benchmarks/cryogenesis/mechanism_genome.json`.
- Create `tests/fixtures/cryogenesis/physical_feature_fixture.json`.
- Create `tests/test_cryogenesis_schemas.py`.
- Create `tests/test_cryogenesis_matching.py`.
- Create `tests/test_cryogenesis_passport.py`.
- Create `tests/test_cryogenesis_sources.py`.
- Create `tests/test_cryogenesis_pipeline.py`.

### API

- Create `glacierkz-api/app/services/cryogenesis_service.py`.
- Create `glacierkz-api/app/routers/cryogenesis.py`.
- Create `glacierkz-api/tests/test_cryogenesis.py`.
- Modify `glacierkz-api/app/main.py`.

### Web

- Create `glacierkz-web/src/lib/cryogenesis.ts`.
- Create `glacierkz-web/src/components/CryoGenesisMap.tsx`.
- Create `glacierkz-web/src/components/DiscoveryPassportPanel.tsx`.
- Create `glacierkz-web/src/app/discovery/page.tsx`.
- Create `glacierkz-web/src/__tests__/cryogenesis.test.tsx`.
- Create `glacierkz-web/e2e/discovery.spec.ts`.
- Modify `glacierkz-web/src/lib/api.ts`.
- Modify `glacierkz-web/src/app/sitemap.ts`.
- Modify the existing primary navigation component identified by
  `rg -l 'risk-twin|operations' glacierkz-web/src/components glacierkz-web/src/app/layout.tsx`.

### Release evidence

- Modify `docs/MODULE_MATURITY.md`.
- Modify `docs/REPRODUCIBILITY.md`.
- Modify `docs/API_REFERENCE.md`.
- Modify `config/coverage_scopes.json`.

## Task 1: Define immutable Release 1 schemas

**Files:**
- Create: `src/cryogenesis/__init__.py`
- Create: `src/cryogenesis/schemas.py`
- Test: `tests/test_cryogenesis_schemas.py`

- [x] **Step 1: Write failing schema tests**

```python
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
```

- [x] **Step 2: Run the tests and verify the import failure**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_schemas.py -q --no-cov
```

Expected: collection fails with `ModuleNotFoundError: No module named 'src.cryogenesis'`.

- [x] **Step 3: Implement the immutable records**

`src/cryogenesis/schemas.py` must define frozen dataclasses:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

QualityState = Literal["observed", "not_observed", "not_applicable", "context_only"]
Split = Literal["development", "temporal_test", "spatial_test", "external_test"]
MatchStatus = Literal["matched", "limited_match", "no_valid_counterfactual"]
SurpriseClass = Literal[
    "observation_inconclusive",
    "comparison_inconclusive",
    "trajectory_consistent",
    "unexplained_divergence_candidate",
]


@dataclass(frozen=True)
class SourceAsset:
    source_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("sha256 must be a lowercase 64-character hexadecimal digest")
        if self.size_bytes < 0:
            raise ValueError("size_bytes must be non-negative")


@dataclass(frozen=True)
class FeatureValue:
    value: float | int | str | None
    unit: str
    observed_at: datetime
    source_id: str
    quality_state: QualityState
    uncertainty: float | None = None

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.uncertainty is not None and self.uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")


@dataclass(frozen=True)
class GlacierFeatureRecord:
    rgi_id: str
    basin_id: str
    region_id: str
    split: Split
    anchor_year: int
    outcome_year: int
    features: dict[str, FeatureValue]
    outcome: FeatureValue | None

    def __post_init__(self) -> None:
        if self.outcome_year <= self.anchor_year:
            raise ValueError("outcome_year must be later than anchor_year")


@dataclass(frozen=True)
class TwinMatch:
    rgi_id: str
    total_distance: float
    component_distances: dict[str, float]
    weight: float


@dataclass(frozen=True)
class MatchResult:
    target_rgi_id: str
    status: MatchStatus
    twins: tuple[TwinMatch, ...]
    rejection_reasons: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DivergenceResult:
    target_outcome: float
    comparator_outcome: float
    raw_divergence: float
    standardized_divergence: float | None
    comparator_interval: tuple[float, float]
    leave_one_out_range: tuple[float, float]


@dataclass(frozen=True)
class DiscoveryPassport:
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


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    errors: tuple[str, ...] = ()
```

Export these records from `src/cryogenesis/__init__.py`.

- [x] **Step 4: Run schema tests**

Run the command from Step 2.

Expected: `3 passed`.

- [x] **Step 5: Commit**

```bash
git add src/cryogenesis tests/test_cryogenesis_schemas.py
git commit -m "feat: define CryoGenesis evidence schemas"
```

## Task 2: Implement leakage checks and deterministic matching

**Files:**
- Create: `src/cryogenesis/cohort.py`
- Create: `src/cryogenesis/matching.py`
- Test: `tests/test_cryogenesis_matching.py`

- [x] **Step 1: Write failing matching tests**

```python
from datetime import datetime, timezone

import pytest

from src.cryogenesis.cohort import validate_pre_outcome_features
from src.cryogenesis.matching import MatchConfig, match_twins
from src.cryogenesis.schemas import FeatureValue, GlacierFeatureRecord


def fv(value: float, year: int, unit: str = "unitless") -> FeatureValue:
    return FeatureValue(value, unit, datetime(year, 7, 1, tzinfo=timezone.utc), "fixture", "observed")


def record(rgi_id: str, area: float, elevation: float, outcome: float, split: str = "development"):
    return GlacierFeatureRecord(
        rgi_id=rgi_id,
        basin_id="B1",
        region_id="R1",
        split=split,
        anchor_year=2020,
        outcome_year=2024,
        features={"area_km2": fv(area, 2020, "km2"), "elevation_m": fv(elevation, 2020, "m")},
        outcome=fv(outcome, 2024, "fraction"),
    )


def test_post_anchor_feature_is_rejected():
    target = record("A", 2.0, 3500, -0.1)
    leaked = dict(target.features)
    leaked["future_velocity"] = fv(10, 2024, "m/year")
    with pytest.raises(ValueError, match="future_velocity"):
        validate_pre_outcome_features(target.__class__(
            **{**target.__dict__, "features": leaked}
        ))


def test_matching_is_deterministic_and_never_matches_self():
    rows = [
        record("A", 2.0, 3500, -0.10),
        record("B", 2.1, 3510, -0.08),
        record("C", 1.9, 3490, -0.12),
        record("D", 2.2, 3530, -0.09),
    ]
    result = match_twins(rows[0], rows, MatchConfig(feature_weights={"area_km2": 1, "elevation_m": 1}))
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
    config = MatchConfig(feature_weights={"area_km2": 1, "elevation_m": 1})
    first = match_twins(rows[0], rows, config)
    changed = [rows[0], *(row.__class__(**{**row.__dict__, "outcome": fv(99, 2024)}) for row in rows[1:])]
    second = match_twins(changed[0], changed, config)
    assert [item.rgi_id for item in first.twins] == [item.rgi_id for item in second.twins]
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_matching.py -q --no-cov
```

Expected: import failure for `src.cryogenesis.cohort`.

- [x] **Step 3: Implement matching**

`cohort.py` must reject every feature with `observed_at.year > anchor_year` and
reject missing required features. `matching.py` must define:

```python
@dataclass(frozen=True)
class MatchConfig:
    feature_weights: dict[str, float]
    hard_calipers: dict[str, float] = field(default_factory=dict)
    maximum_distance: float = 3.0
    maximum_twins: int = 5
    minimum_primary_twins: int = 3
    scale_floor: float = 1e-9
```

Calculate scales from development candidates using interquartile range. For
aspect features use `min(abs(a-b), 360-abs(a-b)) / 180`. Reject self, split
crossing, absent required features and caliper violations. Sort by
`(total_distance, rgi_id)`. Assign inverse-distance weights with the configured
floor and normalise to one.

- [x] **Step 4: Run tests**

Expected: `3 passed`.

- [x] **Step 5: Commit**

```bash
git add src/cryogenesis/cohort.py src/cryogenesis/matching.py tests/test_cryogenesis_matching.py
git commit -m "feat: add leakage-safe glacier twin matching"
```

## Task 3: Measure bounded divergence and classify surprise

**Files:**
- Create: `src/cryogenesis/divergence.py`
- Create: `src/cryogenesis/surprise.py`
- Test: `tests/test_cryogenesis_passport.py`

- [x] **Step 1: Write failing divergence tests**

```python
import pytest

from src.cryogenesis.divergence import estimate_divergence
from src.cryogenesis.surprise import classify_surprise


def test_divergence_uses_weighted_comparator_and_leave_one_out():
    result = estimate_divergence(
        target_outcome=-0.20,
        twin_outcomes=(-0.10, -0.08, -0.12),
        weights=(0.5, 0.25, 0.25),
    )
    assert result.comparator_outcome == pytest.approx(-0.10)
    assert result.raw_divergence == pytest.approx(-0.10)
    assert result.comparator_interval == (-0.12, -0.08)
    assert result.leave_one_out_range[0] <= result.leave_one_out_range[1]


def test_wide_measurement_uncertainty_abstains():
    status = classify_surprise(
        match_status="matched",
        target_outcome=-0.20,
        raw_divergence=-0.10,
        comparator_interval=(-0.12, -0.08),
        measurement_uncertainty=0.20,
    )
    assert status == "observation_inconclusive"


def test_too_few_twins_is_comparison_inconclusive():
    assert classify_surprise(
        match_status="limited_match",
        target_outcome=None,
        raw_divergence=None,
        comparator_interval=None,
        measurement_uncertainty=None,
    ) == "comparison_inconclusive"
```

- [x] **Step 2: Run and verify failure**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_passport.py -q --no-cov
```

Expected: import failure for `src.cryogenesis.divergence`.

- [x] **Step 3: Implement minimal bounded estimators**

`estimate_divergence` validates equal non-empty outcome/weight lengths,
non-negative normalised weights and finite values. Comparator interval is the
observed min/max for Release 1. Standardised divergence is `None` when
comparator spread is zero. Leave-one-out recomputes the comparator after
removing each twin.

`classify_surprise` applies this order:

```python
if match_status != "matched":
    return "comparison_inconclusive"
if measurement_uncertainty is not None and abs(raw_divergence) <= measurement_uncertainty:
    return "observation_inconclusive"
if comparator_interval[0] <= target_outcome <= comparator_interval[1]:
    return "trajectory_consistent"
return "unexplained_divergence_candidate"
```

Pass `target_outcome` explicitly; do not infer it from divergence.

- [x] **Step 4: Run tests**

Expected: `3 passed`.

- [x] **Step 5: Commit**

```bash
git add src/cryogenesis/divergence.py src/cryogenesis/surprise.py tests/test_cryogenesis_passport.py
git commit -m "feat: quantify bounded glacier divergence"
```

## Task 4: Build and verify Discovery Passports

**Files:**
- Create: `src/cryogenesis/mechanisms.py`
- Create: `src/cryogenesis/passport.py`
- Create: `benchmarks/cryogenesis/mechanism_genome.json`
- Create: `benchmarks/cryogenesis/feature_schema.json`
- Extend: `tests/test_cryogenesis_passport.py`

- [x] **Step 1: Add failing passport tests**

```python
import json

from src.cryogenesis.passport import build_passport, passport_to_dict, verify_passport
from src.cryogenesis.schemas import (
    DivergenceResult,
    MatchResult,
    SourceAsset,
    TwinMatch,
)


def passport_payload() -> dict:
    match = MatchResult(
        target_rgi_id="RGI-A",
        status="matched",
        twins=(
            TwinMatch("RGI-B", 0.1, {"area_km2": 0.1}, 0.5),
            TwinMatch("RGI-C", 0.2, {"area_km2": 0.2}, 0.3),
            TwinMatch("RGI-D", 0.3, {"area_km2": 0.3}, 0.2),
        ),
    )
    divergence = DivergenceResult(
        target_outcome=-0.2,
        comparator_outcome=-0.1,
        raw_divergence=-0.1,
        standardized_divergence=-2.0,
        comparator_interval=(-0.12, -0.08),
        leave_one_out_range=(-0.11, -0.09),
    )
    source = SourceAsset("fixture", "fixture.json", "a" * 64, 100)
    passport = build_passport(
        cohort_id="ile-2020-2024-v1",
        target_rgi_id="RGI-A",
        match=match,
        divergence=divergence,
        surprise_class="unexplained_divergence_candidate",
        provenance=(source,),
    )
    return passport_to_dict(passport)


def test_passport_is_canonical_hashed_and_blocks_causal_claims():
    payload = passport_payload()
    assert len(payload["payload_sha256"]) == 64
    assert "causal effect identification" in payload["claims_not_allowed"]
    assert verify_passport(payload).valid


def test_tampered_passport_fails_verification():
    payload = json.loads(json.dumps(passport_payload()))
    payload["divergence"]["raw_divergence"] = 999
    result = verify_passport(payload)
    assert not result.valid
    assert "payload_sha256" in result.errors
```

- [x] **Step 2: Run focused tests**

Expected: failure because `src.cryogenesis.passport` is absent.

- [x] **Step 3: Implement canonical JSON and claim policy**

Use:

```python
def canonical_bytes(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

Calculate SHA-256 after removing `payload_sha256`. Verification validates the
schema, required fields, source digests, claim tier and hash. Hard-code Release
1 blocked claims:

```python
CLAIMS_NOT_ALLOWED = (
    "causal effect identification",
    "mass or volume loss",
    "calibrated GLOF probability",
    "operational warning",
    "validated intervention recommendation",
    "prospective forecast",
)
```

The mechanism catalogue includes the ten IDs in the design and only required
evidence metadata; Release 1 must not add scores.

`feature_schema.json` must contain this required field contract:

```json
{
  "schema": "glaciernet-kz.cryogenesis-features.v1",
  "required": [
    {"name": "anchor_area_km2", "unit": "km2", "source": "annual_mask"},
    {"name": "elevation_min_m", "unit": "m", "source": "rgi_copdem"},
    {"name": "elevation_mean_m", "unit": "m", "source": "rgi_copdem"},
    {"name": "elevation_max_m", "unit": "m", "source": "rgi_copdem"},
    {"name": "elevation_range_m", "unit": "m", "source": "derived_pre_outcome"},
    {"name": "slope_deg", "unit": "degree", "source": "rgi_copdem"},
    {"name": "aspect_sin", "unit": "unitless", "source": "derived_pre_outcome"},
    {"name": "aspect_cos", "unit": "unitless", "source": "derived_pre_outcome"},
    {"name": "summer_temperature_c", "unit": "degree_celsius", "source": "era5_land"},
    {"name": "annual_precipitation_m", "unit": "m", "source": "era5_land"},
    {"name": "snow_depth_m", "unit": "m", "source": "era5_land"},
    {"name": "valid_observation_count", "unit": "count", "source": "annual_mask_provenance"},
    {"name": "label_tier", "unit": "category", "source": "annual_mask_provenance"},
    {"name": "sensor_family", "unit": "category", "source": "annual_mask_provenance"}
  ],
  "outcome": {
    "name": "mapped_area_change_fraction",
    "unit": "fraction",
    "source": "anchor_and_outcome_annual_masks"
  }
}
```

`mechanism_genome.json` contains these records with no score field:

```json
[
  {"id": "temperature_surface_melt", "required_variables": ["summer_temperature_c"], "expected_signature": "mapped-area divergence follows pre-declared temperature exposure", "contradictory_signature": "effect disappears under matched temperature exposure"},
  {"id": "snow_precipitation_deficit", "required_variables": ["annual_precipitation_m", "snow_depth_m"], "expected_signature": "snow deficit precedes divergence", "contradictory_signature": "no pre-divergence snow or precipitation difference"},
  {"id": "thin_debris_enhancement", "required_variables": ["debris_fraction", "surface_temperature"], "expected_signature": "thin debris and elevated surface temperature precede divergence", "contradictory_signature": "debris is absent or insulating"},
  {"id": "thick_debris_insulation", "required_variables": ["debris_fraction", "debris_thickness"], "expected_signature": "thick debris corresponds to reduced mapped-area response", "contradictory_signature": "measured debris is thin"},
  {"id": "proglacial_lake_contact", "required_variables": ["lake_contact", "lake_area_series"], "expected_signature": "lake contact precedes terminus divergence", "contradictory_signature": "no source-reviewed contact"},
  {"id": "dynamic_acceleration", "required_variables": ["surface_velocity"], "expected_signature": "velocity increase precedes mapped-area divergence", "contradictory_signature": "velocity remains stable within uncertainty"},
  {"id": "terrain_shading", "required_variables": ["slope_deg", "aspect_sin", "aspect_cos", "shadow_fraction"], "expected_signature": "radiation exposure separates target and twins", "contradictory_signature": "exposure is balanced after matching"},
  {"id": "fragmentation_geometry", "required_variables": ["perimeter_area_ratio", "fragment_count"], "expected_signature": "fragmentation precedes accelerated mapped-area change", "contradictory_signature": "geometry remains connected"},
  {"id": "observation_or_label_artifact", "required_variables": ["sensor_family", "label_tier", "valid_observation_count"], "expected_signature": "divergence follows sensor or label disagreement", "contradictory_signature": "independent observations agree"},
  {"id": "unresolved_mechanism", "required_variables": [], "expected_signature": "declared mechanisms remain insufficient after quality checks", "contradictory_signature": "a declared mechanism explains and replicates the divergence"}
]
```

- [x] **Step 4: Run passport tests and JSON parse checks**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_passport.py -q --no-cov
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m json.tool \
  benchmarks/cryogenesis/mechanism_genome.json >/dev/null
```

Expected: all tests pass and `json.tool` exits zero.

- [x] **Step 5: Commit**

```bash
git add src/cryogenesis benchmarks/cryogenesis tests/test_cryogenesis_passport.py
git commit -m "feat: add immutable CryoGenesis discovery passports"
```

## Task 5: Construct the physical cohort and command-line pipeline

**Files:**
- Create: `src/cryogenesis/source_registry.py`
- Create: `src/cryogenesis/features.py`
- Create: `src/cryogenesis/evaluation.py`
- Create: `scripts/build_cryogenesis_cohort.py`
- Create: `scripts/validate_cryogenesis_passports.py`
- Create: `benchmarks/cryogenesis/protocol.md`
- Create: `tests/fixtures/cryogenesis/physical_feature_fixture.json`
- Create: `tests/test_cryogenesis_sources.py`
- Create: `tests/test_cryogenesis_pipeline.py`
- Modify: `pyproject.toml`

- [x] **Step 1: Write source and pipeline tests**

```python
from pathlib import Path

import pytest

from src.cryogenesis.source_registry import RegisteredSource, verify_sources


def test_missing_or_changed_source_blocks_cohort(tmp_path: Path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"physical")
    source = RegisteredSource.from_path("source", path, tmp_path)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_sources((source,), tmp_path)
```

Create the fixture with four records and explicit timestamps:

```json
{
  "schema": "glaciernet-kz.cryogenesis-feature-fixture.v1",
  "source_assets": [
    {
      "source_id": "fixture",
      "relative_path": "tests/fixtures/cryogenesis/physical_feature_fixture.json",
      "sha256": "computed_at_runtime",
      "size_bytes": "computed_at_runtime"
    }
  ],
  "records": [
    {"rgi_id": "RGI-A", "basin_id": "B1", "region_id": "R1", "split": "development", "anchor_year": 2020, "outcome_year": 2024, "area_km2": 2.0, "elevation_m": 3500, "outcome_fraction": -0.20},
    {"rgi_id": "RGI-B", "basin_id": "B1", "region_id": "R1", "split": "development", "anchor_year": 2020, "outcome_year": 2024, "area_km2": 2.1, "elevation_m": 3510, "outcome_fraction": -0.10},
    {"rgi_id": "RGI-C", "basin_id": "B1", "region_id": "R1", "split": "development", "anchor_year": 2020, "outcome_year": 2024, "area_km2": 1.9, "elevation_m": 3490, "outcome_fraction": -0.08},
    {"rgi_id": "RGI-D", "basin_id": "B1", "region_id": "R1", "split": "development", "anchor_year": 2020, "outcome_year": 2024, "area_km2": 2.2, "elevation_m": 3530, "outcome_fraction": -0.12}
  ]
}
```

The fixture loader assigns `observed_at` to 1 July of the declared anchor or
outcome year and computes its own source size and digest; the literal
`computed_at_runtime` values never enter a passport.

Pipeline test:

```python
import json
import subprocess
from pathlib import Path


def test_fixture_pipeline_emits_three_twin_engineering_passport(tmp_path: Path):
    command = [
        "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python",
        "scripts/build_cryogenesis_cohort.py",
        "--feature-fixture", "tests/fixtures/cryogenesis/physical_feature_fixture.json",
        "--output-root", str(tmp_path),
        "--anchor-year", "2020",
        "--outcome-year", "2024",
        "--cohort-id", "fixture-v1",
    ]
    subprocess.run(command, check=True)
    passport = json.loads((tmp_path / "passports" / "RGI-A.json").read_text())
    assert passport["match"]["status"] == "matched"
    assert len(passport["match"]["twins"]) == 3
    assert passport["claim_tier"] == "cohort_built"
    assert passport["claims_not_allowed"]
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_sources.py tests/test_cryogenesis_pipeline.py -q --no-cov
```

Expected: imports fail.

- [x] **Step 3: Add explicit NetCDF dependencies**

Add to `pyproject.toml` dependencies:

```toml
"xarray>=2024.1,<2027",
"netCDF4>=1.6,<2",
"pyarrow>=16,<23",
```

Do not add Dask; the regional ERA5 file is opened without chunking.

- [x] **Step 4: Implement physical source extraction**

`source_registry.py` permits these roots only:

```python
REQUIRED_SOURCE_PATHS = {
    "rgi": Path("data/rgi/rgi_study_area.shp"),
    "era5_land": Path("data/climate/era5_land_2000_2025_monthly.nc"),
    "copdem": Path("data/ancillary/copdem"),
    "predictions": Path("predictions"),
}
```

Include every Shapefile sidecar in the RGI digest set. `features.py`:

1. reads RGI with GeoPandas and preserves `rgi_id`;
2. uses RGI geometry attributes for anchor geometry and terrain fields already
   sourced from Copernicus DEM;
3. samples the nearest ERA5-Land grid cell to the glacier centroid using xarray
   and aggregates only months ending on or before 31 December of the anchor
   year;
4. clips one declared annual mask per glacier for anchor and outcome years with
   Rasterio;
5. stores every timestamp, unit, source ID and quality state;
6. excludes a glacier if either mapped-area observation is unavailable.

Fixture mode reads the same schema but is allowed only with
`--feature-fixture`; emitted passports must include
`claim_tier="cohort_built"` unless the fixture declares physical source hashes.

- [x] **Step 5: Implement cohort output and aggregate report**

Write:

```text
<output-root>/
  manifest.json
  features.parquet
  eligibility.csv
  source_assets.json
  build_report.json
  checksums.sha256
  passports/<rgi_id>.json
```

Write feature rows to Parquet with an explicit Arrow schema and stable column
order. The manifest sets `scientific_readiness` to
`insufficient_cohort_size` below 30 eligible glaciers.

- [x] **Step 6: Run fixture pipeline and local preflight**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_sources.py tests/test_cryogenesis_pipeline.py -q --no-cov
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/build_cryogenesis_cohort.py --preflight
```

Expected: tests pass. Preflight reports each required source as `ready` or
exits non-zero with exact missing/checksum/coverage reasons; it never downloads
or fabricates data.

- [x] **Step 7: Commit**

```bash
git add pyproject.toml src/cryogenesis scripts/build_cryogenesis_cohort.py \
  scripts/validate_cryogenesis_passports.py benchmarks/cryogenesis \
  tests/fixtures/cryogenesis tests/test_cryogenesis_sources.py \
  tests/test_cryogenesis_pipeline.py
git commit -m "feat: build physical CryoGenesis cohorts"
```

## Task 6: Expose validated read-only API artefacts

**Files:**
- Create: `glacierkz-api/app/services/cryogenesis_service.py`
- Create: `glacierkz-api/app/routers/cryogenesis.py`
- Create: `glacierkz-api/tests/test_cryogenesis.py`
- Modify: `glacierkz-api/app/main.py`

- [x] **Step 1: Write failing service and router tests**

```python
import json

from fastapi.testclient import TestClient
from app.main import app


def test_service_rejects_invalid_passport(monkeypatch, tmp_path):
    from app.services import cryogenesis_service

    root = tmp_path / "cryogenesis"
    (root / "passports").mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps({"cohort_id": "broken"}))
    (root / "passports" / "RGI-A.json").write_text(json.dumps({"schema": "bad"}))
    monkeypatch.setattr(cryogenesis_service, "CRYOGENESIS_ROOT", root)

    result = cryogenesis_service.get_passport("RGI-A")
    assert result["status"] == "invalid_artifact"
    assert result["claims_not_allowed"]


def test_router_returns_404_without_nearest_glacier_substitution(monkeypatch, tmp_path):
    from app.services import cryogenesis_service

    root = tmp_path / "cryogenesis"
    (root / "passports").mkdir(parents=True)
    monkeypatch.setattr(cryogenesis_service, "CRYOGENESIS_ROOT", root)
    with TestClient(app) as client:
        response = client.get("/api/cryogenesis/glaciers/UNKNOWN/passport")
        assert response.status_code == 404
```

- [x] **Step 2: Run test and verify failure**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  glacierkz-api/tests/test_cryogenesis.py -q --no-cov
```

Expected: import failure.

- [x] **Step 3: Implement service and router**

Resolve the project root with the same fail-closed parent search used by
`scientific_evidence_service.py`, then set the service root:

```python
PROJECT_ROOT = resolve_project_root()
CRYOGENESIS_ROOT = PROJECT_ROOT / "results" / "cryogenesis" / "current"
```

Resolve paths by exact ID using a conservative ID regex and verify that the
resolved path remains under `CRYOGENESIS_ROOT`. Every passport passes
`verify_passport` before return.

Router:

```python
router = APIRouter(prefix="/api/cryogenesis", tags=["cryogenesis"])

@router.get("/status")
def status() -> dict: ...

@router.get("/cohorts")
def cohorts() -> dict: ...

@router.get("/glaciers/{rgi_id}/passport")
def passport(rgi_id: str, cohort_id: str | None = None) -> dict: ...

@router.get("/discoveries")
def discoveries(
    cohort_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict: ...
```

Add the router import, OpenAPI tag and `app.include_router(cryogenesis.router)`
to `main.py`.

- [x] **Step 4: Run API tests**

Expected: all CryoGenesis API tests pass.

- [x] **Step 5: Commit**

```bash
git add glacierkz-api/app/main.py glacierkz-api/app/routers/cryogenesis.py \
  glacierkz-api/app/services/cryogenesis_service.py glacierkz-api/tests/test_cryogenesis.py
git commit -m "feat: expose validated CryoGenesis passports"
```

## Task 7: Build the `/discovery` evidence workspace

**Files:**
- Create: `glacierkz-web/src/lib/cryogenesis.ts`
- Create: `glacierkz-web/src/components/CryoGenesisMap.tsx`
- Create: `glacierkz-web/src/components/DiscoveryPassportPanel.tsx`
- Create: `glacierkz-web/src/app/discovery/page.tsx`
- Create: `glacierkz-web/src/__tests__/cryogenesis.test.tsx`
- Modify: `glacierkz-web/src/lib/api.ts`
- Modify: `glacierkz-web/src/app/sitemap.ts`
- Modify: primary navigation file found by the command in the file map

- [x] **Step 1: Write failing component test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DiscoveryPassportPanel from "@/components/DiscoveryPassportPanel";
import type { DiscoveryPassport } from "@/lib/cryogenesis";

const passport: DiscoveryPassport = {
  schema: "glaciernet-kz.cryogenesis-passport.v1",
  cohort_id: "ile-2020-2024-v1",
  target_rgi_id: "RGI-A",
  claim_tier: "divergence_measured",
  match: {
    target_rgi_id: "RGI-A",
    status: "matched",
    twins: [
      { rgi_id: "RGI-B", total_distance: 0.2, component_distances: { area_km2: 0.1 }, weight: 1 },
    ],
    rejection_reasons: {},
  },
  divergence: {
    target_outcome: -0.2,
    comparator_outcome: -0.1,
    raw_divergence: -0.1,
    standardized_divergence: -2,
    comparator_interval: [-0.12, -0.08],
    leave_one_out_range: [-0.1, -0.1],
  },
  surprise_class: "unexplained_divergence_candidate",
  claims_allowed: ["retrospective mapped-area comparison"],
  claims_not_allowed: ["causal effect identification"],
  provenance: [],
  payload_sha256: "a".repeat(64),
};

describe("DiscoveryPassportPanel", () => {
  it("shows measured divergence next to the causal boundary", () => {
    render(<DiscoveryPassportPanel passport={passport} />);
    expect(screen.getByText(/Unexplained divergence candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/causal effect identification/i)).toBeInTheDocument();
    expect(screen.getByText(/retrospective mapped-area comparison/i)).toBeInTheDocument();
  });
});
```

- [x] **Step 2: Run and verify failure**

Run:

```bash
cd glacierkz-web
npm test -- src/__tests__/cryogenesis.test.tsx
```

Expected: import failure for the new component.

- [x] **Step 3: Add exact TypeScript contracts and fetch functions**

`cryogenesis.ts` mirrors the passport schema. Add to `api.ts`:

```ts
export async function fetchCryoGenesisDiscoveries(): Promise<CryoGenesisDiscoveryList> {
  const res = checkResponse(await fetch(apiUrl("/api/cryogenesis/discoveries")));
  return res.json();
}

export async function fetchCryoGenesisPassport(rgiId: string): Promise<DiscoveryPassport> {
  const res = checkResponse(
    await fetch(apiUrl(`/api/cryogenesis/glaciers/${encodeURIComponent(rgiId)}/passport`)),
  );
  return res.json();
}

export async function fetchGlacier(rgiId: string): Promise<GlacierRecord> {
  const res = checkResponse(
    await fetch(apiUrl(`/api/glaciers/${encodeURIComponent(rgiId)}`)),
  );
  return res.json();
}
```

- [x] **Step 4: Implement accessible workspace**

The page has:

- a real discovery queue;
- target/twin selector;
- target and twin map with labels hidden until click/focus;
- trajectory/comparator summary;
- component distance table;
- supporting, contradicting and missing evidence sections;
- visible retrospective and non-causal boundary;
- downloadable passport JSON link only when supplied by the API;
- map-independent table;
- no demo/synthetic fallback.

The page resolves exact target and twin geometries with `fetchGlacier` and
loads their existing `fetchGlacierSeries` records. A failed exact lookup
removes only that geometry/series and displays its source error; it never
searches for a nearby glacier.

Use a dynamic Leaflet component with SSR disabled, following the existing map
components. Empty and invalid states show the returned reason.

- [x] **Step 5: Run component, lint and build checks**

Run:

```bash
cd glacierkz-web
npm test -- src/__tests__/cryogenesis.test.tsx
npm run lint
npm run build
```

Expected: all commands exit zero.

- [x] **Step 6: Commit**

```bash
git add glacierkz-web/src
git commit -m "feat: add CryoGenesis discovery workspace"
```

## Task 8: Add browser verification and release documentation

**Files:**
- Create: `glacierkz-web/e2e/discovery.spec.ts`
- Modify: `docs/MODULE_MATURITY.md`
- Modify: `docs/REPRODUCIBILITY.md`
- Modify: `docs/API_REFERENCE.md`
- Modify: `config/coverage_scopes.json`

- [x] **Step 1: Write browser test**

```ts
import { expect, test } from "@playwright/test";

test("CryoGenesis shows physical twins and never promotes a causal claim", async ({ page }) => {
  await page.goto("/discovery");
  await expect(page.getByRole("heading", { level: 1, name: /CryoGenesis/i })).toBeVisible();
  await expect(page.getByText(/retrospective mapped-area comparison/i)).toBeVisible();
  await expect(page.getByText(/causal effect identification/i)).toBeVisible();
  await expect(page.getByLabel(/CryoGenesis target and matched twins/i)).toBeVisible();
  await expect(page.locator('[data-evidence-tier="synthetic"]')).toHaveCount(0);
});
```

- [x] **Step 2: Document exact maturity**

Add to `MODULE_MATURITY.md`:

```markdown
## CryoGenesis X

Release 1 is a tested retrospective matched-comparator research baseline. It
measures mapped-area divergence from physical local artefacts and emits
hash-verified Discovery Passports. It does not identify causal effects,
discover physical laws, forecast future retreat, calculate event probability
or issue warnings.
```

Document preflight, cohort build, validation and API checks in
`REPRODUCIBILITY.md`. Document the four endpoints in `API_REFERENCE.md`. Add
`src/cryogenesis` to production scope only after the physical pipeline and API
tests pass; until then classify it as a visible research scope.

- [x] **Step 3: Run focused full verification**

Run:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest \
  tests/test_cryogenesis_schemas.py \
  tests/test_cryogenesis_matching.py \
  tests/test_cryogenesis_passport.py \
  tests/test_cryogenesis_sources.py \
  tests/test_cryogenesis_pipeline.py \
  glacierkz-api/tests/test_cryogenesis.py -q --no-cov
cd glacierkz-web
npm test -- src/__tests__/cryogenesis.test.tsx
npm run lint
npm run build
npm run test:e2e -- e2e/discovery.spec.ts --project=chromium
```

Expected: every command exits zero. If the E2E server is not already running,
build first because Playwright uses `npm run start`.

- [x] **Step 4: Run regression verification**

Run:

```bash
cd /Users/dulatnurlanuly/Downloads/GlacierNET-KZ
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python -m pytest -q --no-cov
cd glacierkz-web
npm test
```

Expected: no regression relative to the current `944 passed, 2 skipped,
65 deselected` Python baseline and current web suite. Record the exact new
counts rather than copying the baseline into release evidence.

- [x] **Step 5: Build and validate one physical local cohort**

Run:

```bash
cd /Users/dulatnurlanuly/Downloads/GlacierNET-KZ
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/build_cryogenesis_cohort.py \
  --cohort-id ile-2016-2024-v1 \
  --anchor-year 2016 \
  --outcome-year 2024 \
  --output-root results/cryogenesis/current
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/validate_cryogenesis_passports.py results/cryogenesis/current
```

Expected: either a validated physical cohort with at least one target and three
twins, or a non-zero fail-closed report naming the exact data insufficiency.
Do not replace a failed physical run with the fixture for product evidence.

- [x] **Step 6: Commit release evidence**

```bash
git add docs config/coverage_scopes.json glacierkz-web/e2e/discovery.spec.ts \
  results/cryogenesis/current
git commit -m "test: verify CryoGenesis release one"
```

Before adding `results/cryogenesis/current`, confirm it contains only compact
JSON/CSV/manifests and no large imagery or secret paths.

## Task 9: Final integrity review

**Files:**
- Review all files changed by Tasks 1–8.

- [x] **Step 1: Scan for prohibited claims and placeholders**

Run:

```bash
rg -n -i \
  'TBD|TODO|placeholder|caused retreat|new physical law discovered|operational warning|validated intervention' \
  src/cryogenesis glacierkz-api/app/routers/cryogenesis.py \
  glacierkz-api/app/services/cryogenesis_service.py \
  glacierkz-web/src/app/discovery docs benchmarks/cryogenesis
```

Expected: only explicit blocked-claim and non-goal text; no placeholder markers.

- [x] **Step 2: Check repository integrity**

Run:

```bash
git diff --check
git status --short
git log --oneline -10
```

Expected: no whitespace errors, only intentional uncommitted changes, and one
small commit per completed task.

- [x] **Step 3: Update the plan checkboxes and final handoff**

Mark completed steps in this plan. Report:

- physical cohort size and source hashes;
- eligible/no-match/limited-match counts;
- passport verifier results;
- exact Python/web/E2E test counts;
- scientific-readiness gate;
- claims allowed and still blocked;
- commit IDs;
- whether the branch was pushed.
