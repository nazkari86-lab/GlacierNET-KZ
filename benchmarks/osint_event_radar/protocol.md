# OSINT Event Radar retrospective benchmark

## Question

Does a source-backed OSINT signal improve the choice and timing of the next
cryosphere observation without increasing false alarms?

## Evaluation unit

One unit is a basin-period snapshot with a frozen cutoff time. Event snapshots
must precede a primary-source-verified event. Controls must have comparable
sensor/source coverage and a verified no-event window.

## Required splits

- `development`: feature and rule design;
- `temporal_test`: later periods in held-out time;
- `external_test`: held-out basins/geography.

A basin cannot cross splits. A story, revised bulletin, or database record
published after the cutoff is hidden even if it describes an earlier event.
Each snapshot has a content manifest and SHA-256 digest.

## Comparison ladder

1. physical Risk Twin without OSINT;
2. keyword/source-tier Event Radar;
3. geolocated and deduplicated Event Radar;
4. learned fusion model, only after rows 1–3 are frozen.

All systems receive the same physical observations and cutoff.

## Metrics

- source-level and event-level precision/recall;
- false observation escalations per basin-month;
- median usable detection lead time;
- Recall@5/Recall@10 for observation priority;
- calibration error and Brier score only for a declared probability model;
- abstention coverage and selective risk;
- performance under one-source outage and duplicate-story stress.

Confidence intervals use basin-level paired bootstrap resampling.

## Claim gate

No predictive metric is computed until there are primary-source-verified
events, coverage-matched controls, immutable pre-event snapshots, at least two
independent event sources, and complete development/temporal/external splits.
Before that point the project may claim only an implemented Event Radar and a
measured evidence-readiness gate.

