# Central Asia Cascade Benchmark protocol

## Purpose

This benchmark evaluates whether a cryosphere system helps a reviewer decide
which basin to inspect and which observation to acquire next. It does not
validate an operational warning service.

## Evaluation units

- A `basin snapshot` contains only evidence available at its cutoff time.
- An `event replay` is anchored to a documented event time and uses one or more
  pre-event lead-time cutoffs.
- A `non-event control` is a basin-period with comparable observation coverage
  and no documented event in the declared verification window.
- Basin, event and observation identifiers must remain stable across releases.

## Required splits

1. Development basins for model fitting and decision-rule design.
2. Temporal test snapshots that occur after all development evidence.
3. Spatial external test basins from a region excluded from development.
4. Event and non-event controls grouped by basin; no basin may cross splits.

The split manifest is immutable after evaluation starts and must record a
SHA-256 digest. Hyperparameters, thresholds and calibration are frozen using
development data only.

## Replay and leakage rules

For an event at time `T` and requested lead time `L`, the model receives only
observations whose acquisition timestamp is at or before `T - L`. Publication
dates, revised inventories and products generated after the cutoff are also
forbidden even if they describe an earlier acquisition. Every replay must save
the allowed and hidden observation identifiers.

## Primary metrics

- Basin prioritisation: Recall@5, Recall@10, mean reciprocal rank.
- Warning-style evaluation: median usable lead time, missed events, false
  alerts per basin-year. These are research metrics, not authority alerts.
- Probabilistic quality, only after calibration: CRPS and interval coverage.
- Decision quality: regret relative to the best action available in hindsight.
- Observation selection: realised uncertainty or decision-loss reduction after
  the selected observation arrives.
- Abstention: coverage, selective risk and failure rate on abstained versus
  answered cases.
- Resilience hypotheses: whether model margin improves ranking over lake area,
  static susceptibility and Risk Twin without stress testing.
- Diagnostic robustness: weather-conditioned null tests, cadence degradation,
  artificial missingness and seasonal detrending sensitivity.

All metrics are reported with basin-level bootstrap confidence intervals.
Results must be stratified by region, sensor availability and evidence quality.

## Frozen comparison ladder

1. Lake area or area growth.
2. Static susceptibility score.
3. A declared ML hazard classifier.
4. Risk Twin without virtual stress testing.
5. Resilience-aware Risk Twin with the same evidence cutoff.

The resilience model must not receive more recent observations than any
baseline. Model margins that do not cross within the tested scenario surface
remain right-censored. Critical-slowing diagnostics are evaluated individually
and jointly; no single autocorrelation trend is treated as an event label.

## Claim gate

The benchmark is evidence-complete only when the manifest contains verified
events, non-event controls, disjoint development/temporal/external splits,
source citations and snapshot hashes. Until then, only implementation and
structural-readiness claims are permitted.
