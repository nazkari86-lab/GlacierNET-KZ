# Central Asia Cascade Benchmark dataset card

## Current status

**Structure ready; evidence incomplete.** No event probabilities, warning
performance or Central Asia generalisation claims may be derived from the
empty manifest committed with this repository.

## Intended evidence

The benchmark is designed for documented glacier-lake outburst floods and
related cascading cryosphere events in Central Asia, paired with comparable
non-event basin-period controls. Each record must distinguish:

- event occurrence and time confidence;
- primary and corroborating source citations;
- glacier, lake, slope, dam, channel and exposed-asset observations;
- acquisition time, publication time and uncertainty;
- exact pre-event cutoff used by replay;
- geographic region and split assignment.

## Known limitations

- Historical event catalogues are incomplete and reporting is spatially biased.
- “No event reported” is not automatically a verified negative.
- Remote sensing cannot directly establish moraine internal structure,
  bathymetry, freeboard or channel conveyance without suitable field evidence.
- Inventory revisions can leak post-event knowledge into retrospective inputs.
- A useful ranking model is not equivalent to a calibrated event-probability
  model or an official early-warning service.

## Governance

Every accepted event requires source review. Ambiguous dates remain explicit
intervals rather than being converted to precise timestamps. People and
critical infrastructure layers must use aggregated, licensed data. Releases
must include provenance, checksums and a changelog of corrected labels.
