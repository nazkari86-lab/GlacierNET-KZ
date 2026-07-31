# Source-backed OSINT Event Radar

## Purpose

The Event Radar turns a current external report into a reviewable acquisition
task:

`source record → normalized metadata → source coordinates → selected RGI
glacier → distance and scope → next observation`.

It is not a news-based GLOF predictor. A nearby earthquake, flood report, or
mudflow bulletin can justify checking a new SAR/optical scene or an official
field bulletin. It cannot by itself prove damage, establish causality, or
provide a calibrated event probability.

## Implemented sources

| Source | Default | What is retained | Intended role |
|---|---:|---|---|
| USGS Earthquake Catalog | live | event id, title, magnitude, time, coordinates, canonical URL | regional seismic trigger context |
| GDACS | live | event id/type, alert metadata, time, coordinates, canonical URL | multilateral event corroboration |
| Kazhydromet | configured feed | relevant RSS/Atom metadata and link | official weather/mudflow bulletin review |
| Kazakhstan MCS | configured feed | relevant RSS/Atom metadata and link | official warning and field-operation review |
| ReliefWeb | approved appname | relevant report title/date/country/link | curated humanitarian report discovery |
| GDELT Cloud | API key | relevant event-card metadata, resolved coordinates, story link | multilingual open-news discovery |

Article and bulletin bodies are not mirrored. The cache contains normalized
metadata, short source descriptions, coordinates, a canonical link, the
fetch timestamp, and a SHA-256 content digest.

## API

```text
GET /api/osint/events
GET /api/osint/events?rgi_id=RGI2000-v7.0-G-13-33843
GET /api/osint/events?event_type=earthquake&scope=regional_trigger_context
GET /api/osint/events?refresh=true
GET /api/osint/sources
GET /api/osint/readiness
```

When `rgi_id` is supplied, every retained regional signal is recomputed against
that exact glacier. This avoids the misleading behaviour of showing an event
only for whichever glacier happened to be globally nearest.

## Deterministic evidence fields

- `source_tier` describes the publisher/catalogue, not the truth of a causal
  interpretation.
- `distance_to_glacier_km` is a Haversine distance to the RGI centroid.
- `link_scope` is one of `near_glacier` (≤25 km),
  `regional_trigger_context` (25–120 km), `broad_context` (120–350 km), or
  `unresolved`.
- `evidence_confidence_0_1` summarizes source tier, metadata completeness,
  recency, and spatial specificity. It is not physical-event confidence.
- `observation_priority_0_100` ranks the usefulness of checking new evidence.
  It is not danger, impact, or GLOF probability.
- `hazard_probability` is always `null`.

## Reliability controls

- bounded source timeouts and retries;
- a 15-minute default cache;
- atomic cache replacement;
- stale-cache fallback when live sources fail;
- canonical URL/source-id deduplication;
- no article-body persistence;
- explicit source-health status;
- no marker for an unresolved location;
- source-specific recommended action;
- fail-closed claim and readiness endpoints.

The current deduplication collapses exact canonical records. Cross-publisher
story clustering remains deliberately absent until it has a labelled
near-duplicate evaluation set.

## Optional configuration

```dotenv
OSINT_CACHE_TTL_SECONDS=900
OSINT_LOOKBACK_DAYS=30
KAZHYDROMET_OSINT_FEEDS=https://example.gov.kz/feed.xml
GOV_KZ_OSINT_FEEDS=https://example.gov.kz/mcs-feed.xml
RELIEFWEB_APPNAME=pre-approved-appname
GDELT_CLOUD_API_KEY=gdelt_sk_...
```

USGS and GDACS need no credentials. ReliefWeb requires a pre-approved appname.
GDELT Cloud requires a bearer key. Feed URLs should be added only after their
publisher and update semantics have been checked.

## Validation needed before prediction

A news/event model must not be trained on the current live queue. Prediction
requires a frozen retrospective cohort containing:

1. source-reviewed events and explicit non-event controls;
2. immutable pre-event snapshots, excluding post-event reporting;
3. geographic and temporal splits that prevent leakage;
4. source-outage and duplicate-story stress tests;
5. recall, precision, false alerts per basin-month, detection lead time, and
   calibration error;
6. prospective shadow-mode validation.

Until those conditions are met, OSINT is useful for *where to look next*, not
for *what will happen*.
