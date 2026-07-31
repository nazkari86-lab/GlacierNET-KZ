# Dataset card: OSINT Event Radar benchmark

## Current state

No strict event/control rows are published yet. This is intentional: current
live API results are operational metadata, not ground-truth labels.

## Required future tables

- `tables/events.csv`: `event_id`, `basin_id`, `event_time`, `source_id`,
  `primary_source_url`, `primary_source_verified`,
  `eligible_for_strict_benchmark`, `split`.
- `tables/controls.csv`: `control_id`, `basin_id`, `window_start`,
  `window_end`, `absence_window_verified`, `coverage_matched`, `split`.
- `manifests/pre_event_snapshots.jsonl`: immutable snapshot id, cutoff, split,
  visible source records, hidden post-cutoff records, and manifest SHA-256.

Personal identifiers and full article bodies are excluded. Canonical URLs and
short normalized metadata are retained only when licensing and source terms
permit.
