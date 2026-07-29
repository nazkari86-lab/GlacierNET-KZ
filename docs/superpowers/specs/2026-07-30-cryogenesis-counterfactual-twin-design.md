# GlacierNET-KZ CryoGenesis X — Counterfactual Twin Discovery design

## Objective

Add a scientifically bounded discovery layer to GlacierNET-KZ that asks why
otherwise comparable glaciers diverge over time. The first release builds a
reproducible `Counterfactual Twin Bank`, measures divergence using only physical
local artefacts, and emits hypothesis-screening records that explicitly retain
supporting, contradicting and missing evidence.

CryoGenesis X is not an operational warning system and does not automatically
discover causal laws. Its first validated contribution is narrower:

> Given a target glacier, an anchor year and a later outcome year, identify
> comparable glaciers using anchor-time information only, quantify whether the
> target's observed trajectory is unusual relative to those comparators, and
> state which declared explanatory observations are still missing. Ranking the
> best discriminating observation is introduced only after retrospective
> validation in Release 3.

The release must make a negative result useful. No acceptable twin or no
reliable outcome produces an explicit abstention, not a synthetic comparison or
an AI-generated explanation. If no declared explanatory observation is
available, the passport records the evidence gap without ranking its value.

`Counterfactual twin` is a product name for a leakage-safe matched comparator.
Release 1 does not claim that the matched outcome identifies the target's
causal potential outcome. The UI, API and exports must retain that distinction.

## Product and scientific principles

```text
physical source artefacts
→ pre-outcome feature contract
→ leakage-safe comparable glaciers
→ measured divergence with uncertainty
→ competing declared hypotheses
→ falsifying observation request
→ evidence-bounded discovery passport
```

The system separates four statements:

1. `observed`: a value is read or derived from a registered physical artefact;
2. `comparable`: the target and candidate pass declared matching diagnostics;
3. `unusual`: the target outcome differs from its matched cohort under the
   declared metric and uncertainty procedure;
4. `mechanism_candidate`: a hypothesis survives the first screening stage.

None of these statements alone is a causal claim.

## Why this is a separate module

The existing segmentation path estimates annual glacier masks. The Risk Twin
assimilates partial observations, propagates declared model uncertainty and
ranks evidence actions. CryoGenesis has a different responsibility: comparing
alternative scientific explanations and recording what would falsify them.

The module therefore lives under `src/cryogenesis` and consumes versioned
outputs from the existing project. It must not import UI code or mutate Risk
Twin state. Risk Twin integration begins only after a CryoGenesis result passes
the replication gates defined below.

## Delivery programme

### Release 1 — Counterfactual Twin Bank

This is the first implementation boundary.

- Build a versioned glacier cohort from registered RGI geometry, annual local
  analysis artefacts, DEM-derived terrain and ERA5-Land climate context.
- Define an immutable pre-outcome feature schema and retain source provenance
  for every feature.
- Match each target to eligible comparison glaciers without using future
  outcomes.
- Calculate divergence, comparator intervals, aggregate bootstrap intervals
  and matching diagnostics.
- Emit a fail-closed `Discovery Passport`.
- Expose read-only API endpoints and a focused web workspace for inspecting
  the target, twins, evidence and claim limits.

### Release 2 — Rival Hypothesis Tournament

- Add a fixed, versioned Mechanism Genome for mapped-area divergence.
- Evaluate simple rival explanation models using temporal and spatial
  holdouts.
- Preserve failed models, negative controls and contradictions.
- Separate observation error, transfer failure and candidate mechanism
  surprise.

### Release 3 — Retrospective Active Falsification

- Hide one already available observation channel at a time.
- Rank which hidden observation would best discriminate rival hypotheses.
- Reveal the observation and measure realised information gain.
- Compare against random selection, uncertainty sampling and the existing
  model-based Value of Information baseline.

### Release 4 — Multi-environment replication

- Freeze all features, matching rules and hypothesis thresholds.
- Evaluate on an external region that was absent from development.
- Test whether effect direction and predictive residual structure remain
  stable across regions.
- Promote only externally replicated candidates to Risk Twin screening inputs.

### Release 5 — Physics-constrained symbolic discovery

- Search for compact equations only after a mechanism candidate passes temporal
  and spatial replication.
- Enforce dimensional validity, declared monotonicity constraints and an
  explicit environment-specific discrepancy term.
- Retain a Pareto front of accuracy versus complexity rather than selecting one
  equation after inspecting the external test.

## First scientific question

Release 1 answers one question:

> Which glaciers in the supported Central Asian cohort show an unusually large
> or small mapped-area change relative to glaciers with similar
> pre-outcome geometry, terrain, climate and observation quality?

The primary outcome is fractional mapped-area change between one anchor year
and one outcome year:

\[
Y_i = \frac{A_{i,t_1} - A_{i,t_0}}{A_{i,t_0}}.
\]

The wording `mapped-area change` is mandatory while masks are RGI-derived
silver or provisional labels. It must not be rendered as mass loss, volume
loss, melt rate or independently verified glacier retreat.

Release 1 is retrospective. It uses outcomes observed over the same completed
window for the target and its twins. It does not claim that a twin's completed
outcome would have been available as a real-time forecast at the anchor date.

Velocity, lake contact, debris and snow persistence are candidate explanatory
observations in later releases. They are not additional primary outcomes in
Release 1.

## Data contract

### Required source families

| Family | Initial use | Failure behaviour |
|---|---|---|
| RGI 7 geometry and stable glacier ID | identity, anchor geometry | target excluded |
| Local annual analysis artefacts | anchor and outcome mapped area | pair unavailable |
| Copernicus DEM GLO-30 | elevation, slope, aspect, relief | candidate excluded |
| ERA5-Land local subset | pre-anchor climate summaries | candidate excluded |
| Analysis provenance and quality flags | observation-quality matching | candidate excluded |

### Optional source families

| Family | Later use | Missing-state behaviour |
|---|---|---|
| Sentinel-1 velocity evidence | dynamic hypothesis | `not_observed` |
| JRC Global Surface Water | lake-contact screening | `context_only` |
| Glacier/lake candidates | lake hypothesis | `unreviewed_candidate` |
| WorldCover and debris products | surface hypothesis | `not_observed` |
| ICESat-2 or elevation differencing | thinning hypothesis | `not_observed` |

An optional source may not silently become zero. Missing, not applicable and
measured zero are distinct typed states.

### Cohort manifest

Every cohort build writes:

```text
results/cryogenesis/cohorts/<cohort_id>/
  manifest.json
  features.parquet
  eligibility.csv
  source_assets.json
  build_report.json
  checksums.sha256
```

The manifest records:

- schema and builder versions;
- git commit;
- source paths and hashes;
- target region and glacier IDs;
- anchor and outcome years;
- feature definitions and units;
- exclusion counts and reasons;
- split assignment;
- random seed;
- environment and dependency versions.

The build is deterministic for the same manifest and source hashes.

## Feature schema

Release 1 permits only features whose timestamps are at or before the anchor
date.

### Identity and grouping

- `rgi_id`;
- `basin_id`;
- `region_id`;
- geometry source and acquisition/reference date;
- development, temporal-test or spatial-test split.

### Geometry and terrain

- anchor mapped area in square metres;
- perimeter and compactness;
- minimum, median and maximum elevation;
- elevation range;
- median slope;
- circular aspect encoded as sine and cosine;
- relief;
- hypsometric-bin fractions.

### Pre-anchor climate

- mean summer temperature;
- positive degree-day proxy when source cadence permits;
- annual and warm-season precipitation;
- snow-depth summary;
- anomalies relative to a declared baseline;
- number of valid source months.

### Observation quality

- valid-pixel fraction;
- cloud/shadow or source-quality flags;
- number of independent annual observations;
- label tier;
- source sensor family;
- segmentation/model version;
- boundary uncertainty when available.

### Leakage exclusions

The following are forbidden during matching:

- outcome-year area or any transform of it;
- outcome-year imagery embeddings;
- post-anchor lake or velocity observations;
- future event labels;
- any feature created from a model trained using target outcome labels unless
  the full model and target split are declared leakage-safe.

The cohort validator fails if a feature timestamp exceeds the anchor cutoff.

## Matching design

### Eligibility

A comparison candidate must:

- be a different stable glacier ID;
- belong to the same declared development scope;
- have the required source families;
- pass source-quality thresholds;
- have valid anchor and outcome observations;
- not cross a frozen split boundary;
- satisfy hard calipers on anchor area and elevation range.

No glacier may be both target and comparison across a train/test boundary.

### Distance

Release 1 uses a transparent mixed-feature distance:

- robust-scaled continuous variables;
- circular distance for aspect;
- weighted absolute differences for climate;
- explicit penalties for differing sensor and label tiers;
- no learned outcome-dependent representation.

Feature weights are declared before test evaluation and saved in the cohort
manifest. The implementation returns component-level distances so a reviewer
can see why a candidate was selected.

For continuous feature \(k\), distance is the absolute difference divided by
the development-cohort interquartile range, with a documented finite floor for
zero-spread features. Aspect uses circular angular distance. Categorical
quality and sensor differences use fixed manifest-declared penalties. The total
distance is the weighted mean over jointly observed required features; required
missing values make the candidate ineligible rather than changing the
denominator.

### Twin set

The matcher returns up to five candidates within the declared maximum distance.
It does not always force five matches.

Status is:

- `matched` when at least three candidates pass all checks;
- `limited_match` when one or two candidates pass;
- `no_valid_counterfactual` when none pass.

Only `matched` targets enter the primary aggregate benchmark. Limited matches
remain visible as exploratory case studies.

### Matching diagnostics

Every target records:

- total and component distances;
- caliper margins;
- pre-match and post-match standardized differences;
- support/overlap warnings;
- candidate rejection reasons;
- sensitivity to removing each matching feature.

## Divergence estimation

For target \(i\) and matched set \(N(i)\):

\[
D_i = Y_i - \sum_{j \in N(i)} w_{ij}Y_j,
\qquad
\sum_j w_{ij}=1.
\]

Weights are non-negative and decrease with matching distance. The output
includes:

- target outcome;
- weighted comparator outcome;
- raw divergence;
- standardized divergence;
- comparator spread;
- weighted empirical comparator interval;
- propagated measurement-uncertainty interval when the source reports
  uncertainty;
- leave-one-twin-out sensitivity;
- area-observation uncertainty propagation when available.

Aggregate benchmark confidence intervals use basin-level bootstrap resampling,
falling back to glacier-level resampling only when the report explicitly states
that independent basin count is insufficient. Patch- or pixel-level resampling
is forbidden. Target-level intervals are labelled comparator or propagated
uncertainty intervals, not confidence intervals for a causal effect.

The system never converts divergence into event probability or causal effect.

## Surprise classification

Release 1 classifies result quality, not physical mechanism:

| Class | Meaning |
|---|---|
| `observation_inconclusive` | source disagreement or uncertainty can explain divergence |
| `comparison_inconclusive` | overlap or twin count is insufficient |
| `trajectory_consistent` | target lies within declared comparator spread |
| `unexplained_divergence_candidate` | divergence remains after declared quality and overlap checks |

`unexplained_divergence_candidate` is a queue entry for Release 2. It is not a
new-physics claim.

## Mechanism Genome contract

Release 1 ships the schema and a conservative initial catalogue but does not
score physical mechanisms.

Initial mechanism identifiers:

- `temperature_surface_melt`;
- `snow_precipitation_deficit`;
- `thin_debris_enhancement`;
- `thick_debris_insulation`;
- `proglacial_lake_contact`;
- `dynamic_acceleration`;
- `terrain_shading`;
- `fragmentation_geometry`;
- `observation_or_label_artifact`;
- `unresolved_mechanism`.

Each record defines:

- human-readable statement;
- required variables;
- expected temporal order;
- expected and contradictory signatures;
- possible confounders;
- minimum discriminating observation;
- allowed claim tier;
- references;
- version.

The language model may explain a returned record. It may not invent, promote or
score mechanisms outside this catalogue.

## Discovery Passport

One immutable passport is emitted per target/cohort run:

```json
{
  "schema": "glaciernet-kz.cryogenesis-passport.v1",
  "target": {},
  "cohort": {},
  "anchor_cutoff": "",
  "outcome_window": {},
  "twins": [],
  "matching_diagnostics": {},
  "divergence": {},
  "surprise_class": "",
  "hypotheses": [],
  "supporting_evidence": [],
  "contradicting_evidence": [],
  "missing_evidence": [],
  "negative_controls": [],
  "claim_tier": "",
  "claims_allowed": [],
  "claims_not_allowed": [],
  "provenance": [],
  "hashes": {}
}
```

Passport claim tiers:

1. `cohort_built`;
2. `comparison_valid`;
3. `divergence_measured`;
4. `hypothesis_screened`;
5. `temporally_replicated`;
6. `spatially_replicated`;
7. `externally_replicated`;
8. `field_consistent`;
9. `mechanism_candidate`.

Promotion is performed by validators against evidence, never by editing the
tier directly.

## Module architecture

```text
src/cryogenesis/
  __init__.py
  schemas.py
  source_registry.py
  features.py
  cohort.py
  matching.py
  divergence.py
  surprise.py
  mechanisms.py
  passport.py
  evaluation.py

scripts/
  build_cryogenesis_cohort.py
  run_counterfactual_twin_benchmark.py
  validate_cryogenesis_passports.py

benchmarks/cryogenesis/
  protocol.md
  feature_schema.json
  mechanism_genome.json
  manifests/

results/cryogenesis/
  cohorts/
  passports/
  reports/
```

Each module has one responsibility:

- `source_registry` resolves only registered local physical artefacts;
- `features` computes pre-outcome values and provenance;
- `cohort` applies eligibility and frozen split rules;
- `matching` selects twins and emits diagnostics;
- `divergence` estimates outcome differences and uncertainty;
- `surprise` maps diagnostics to bounded queue states;
- `mechanisms` validates the fixed catalogue;
- `passport` serialises immutable evidence;
- `evaluation` calculates aggregate benchmark metrics.

## Read-only API

The API composes saved, validated artefacts. It does not run cohort construction
or expensive matching from a public request.

```text
GET /api/cryogenesis/status
GET /api/cryogenesis/cohorts
GET /api/cryogenesis/cohorts/{cohort_id}
GET /api/cryogenesis/glaciers/{rgi_id}/twins?cohort_id=...
GET /api/cryogenesis/glaciers/{rgi_id}/passport?cohort_id=...
GET /api/cryogenesis/discoveries?cohort_id=...&status=...
```

API rules:

- unknown IDs return `404`, never nearest-object substitution;
- invalid or incomplete passports return a typed unavailable state;
- numerical values are returned with units and evidence tier;
- all source-backed geometries retain source IDs;
- paths outside registered result roots are never exposed;
- API responses contain `claims_not_allowed`.

## Web workspace

Add one route: `/discovery`.

### Primary layout

1. Search or choose a real glacier.
2. Select an available validated cohort.
3. View the target and matched twins on one map.
4. Inspect the observed trajectory and comparator envelope.
5. Read matching diagnostics and divergence.
6. Review supporting, contradicting and missing evidence.
7. Open the Discovery Passport.

### Map behaviour

- labels remain hidden until hover, click or keyboard focus;
- target and each twin use distinguishable symbols and accessible patterns;
- map layers never imply hydrological linkage unless a source provides it;
- a readable table provides the same information without the map;
- external basemap failure leaves local vectors and evidence inspection usable.

### Claim language

Allowed:

- `mapped area changed`;
- `matched cohort`;
- `comparison is limited`;
- `unexplained divergence candidate`;
- `additional observation required`.

Blocked:

- `this factor caused retreat`;
- `new physical law discovered`;
- `GLOF risk increased by X%`;
- `warning`;
- `validated intervention`.

## Active falsification boundary

Release 1 may display a missing-evidence priority derived from declared
availability and hypothesis requirements. It must not claim expected
information gain until Release 3 validates the retrospective acquisition
simulator.

Release 3 will define:

\[
a^\star = \arg\max_a
\mathbb E[I(M;y_a\mid D)]-\lambda C(a)-\rho R_{\mathrm{invalid}}(a),
\]

but this score remains absent from Release 1 API and UI.

## Evaluation protocol

### Split design

- development glaciers define feature weights, calipers and thresholds;
- temporal test outcomes occur after every development observation;
- spatial test glaciers belong to frozen basins excluded from development;
- an external region remains untouched until Release 4.

The Release 1 benchmark is a retrospective discovery benchmark, not a forecast
benchmark. Matching rules are frozen on development data, but target and
comparator outcomes are revealed only to calculate completed-window divergence.
Any later claim about prospective prediction requires a separate protocol that
hides every outcome unavailable at the decision cutoff.

### Release 1 primary metrics

- eligible-target coverage;
- mean valid twin count;
- matching distance distribution;
- pre/post-match standardized feature differences;
- no-match rate;
- outcome observation coverage;
- divergence interval width;
- leave-one-twin-out stability;
- abstention rate by reason;
- passport verifier pass rate.

### Negative controls

- shuffled outcome years;
- randomly permuted glacier IDs within a region;
- impossible post-anchor feature injection, which the leakage validator must
  reject;
- duplicated geometry under a new ID, which the identity validator must flag;
- degraded observation quality, which must widen uncertainty or trigger
  abstention rather than increase confidence.

### Baselines

- nearest geographic neighbour;
- region mean;
- unweighted nearest neighbours;
- matching without quality variables;
- robust regression residual without matching.

## Test strategy

### Unit tests

- source-state typing;
- feature timestamps and units;
- leakage detection;
- circular aspect distance;
- hard calipers;
- deterministic tie-breaking;
- missing optional values;
- match-status transitions;
- basin-level bootstrap and the declared glacier-level fallback;
- passport schema and claim-tier validator.

### Property tests

- future outcomes never alter matching;
- reordering candidates does not change deterministic output;
- increasing source uncertainty cannot narrow the propagated interval;
- removing all valid twins always produces abstention;
- no weight is negative and twin weights sum to one;
- a target can never match itself.

### API tests

- real saved passport retrieval;
- unknown glacier and cohort handling;
- incomplete/invalid passport rejection;
- no arbitrary path access;
- claims and units always present.

### Web tests

- target/twin map and table agree;
- labels are hidden by default;
- no synthetic object appears in empty states;
- unavailable cohort has a clear explanation;
- keyboard navigation and reduced motion;
- basemap failure preserves local evidence.

### End-to-end test

Build one small physical-data fixture, generate a cohort, validate passports,
serve one target through the API and inspect it in `/discovery`. The test must
assert the same IDs, outcomes, hashes, claim tier and allowed/blocked language
at every layer.

## Failure handling

- Missing required source: exclude the glacier and retain the reason.
- Invalid checksum: block the cohort.
- Unsupported CRS: fail preprocessing; never guess coordinates.
- Inadequate temporal overlap: no comparison.
- Too few twins: `limited_match` or `no_valid_counterfactual`.
- Wide interval: `observation_inconclusive`.
- Conflicting source versions: block promotion and list both records.
- API unavailable: the UI may show a previously loaded passport only if its
  hash and generated-at time remain visible.
- AI unavailable: all physical evidence and conclusions remain accessible.

## Safety and governance

- Release 1 is read-only and initiates no satellite order, UAV flight, field
  task, warning or infrastructure intervention.
- User-supplied observations remain `requires_provenance_review`.
- Exact sensitive infrastructure details follow the existing access policy.
- Discovery status is scientific screening, not emergency authority advice.
- A language model cannot promote claim tiers or rewrite evidence hashes.

## Acceptance criteria for Release 1

Release 1 is complete only when:

1. a deterministic cohort and checksum manifest are built from physical local
   sources;
2. every feature has a timestamp, unit, source and quality state;
3. leakage tests reject post-anchor inputs;
4. matching emits component distances, calipers and rejection reasons;
5. no-match and uncertain cases abstain without synthetic fallback;
6. each target has a comparator/measurement interval and aggregate uncertainty
   uses basin-level bootstrap with the declared fallback;
7. every returned target has a schema-valid Discovery Passport;
8. the read-only API serves only validated saved artefacts;
9. `/discovery` shows target, twins, trajectories, limitations and provenance;
10. unit, property, API, web and end-to-end tests pass;
11. documentation states that mapped-area divergence is not causal retreat,
    mass loss, event probability or warning;
12. the existing strict project evidence boundaries remain unchanged.

The end-to-end release requires at least one physical target with three valid
physical twins. If fewer than 30 independent eligible glaciers are available,
the aggregate scientific-readiness gate remains `insufficient_cohort_size`
even when the software acceptance criteria pass. This threshold is a release
guard against presenting a tiny engineering cohort as population evidence; it
is not a universal statistical standard.

## Explicit non-goals for Release 1

- autonomous scientific law discovery;
- causal effect identification;
- physical mass-balance inversion;
- calibrated GLOF probability;
- intervention recommendation;
- automated purchase or ordering of observations;
- new foundation-model training;
- global glacier coverage;
- field-validated or expert-adjudicated claims;
- automatic Risk Twin risk-score changes.

## First implementation plan boundary

The first implementation plan covers Release 1 only:

1. schemas and source registry;
2. physical cohort builder;
3. leakage-safe matching and diagnostics;
4. divergence and uncertainty;
5. immutable Discovery Passport;
6. read-only API;
7. `/discovery` evidence workspace;
8. focused tests and reproducibility documentation.

Releases 2–5 require separate reviewed designs because they introduce
hypothesis scoring, active observation value, external causal transport and
equation discovery.
