# Automatic Provisional Cohorts

These cohorts were produced automatically from locally available RGI 7.0
polygons and satellite/terrain data. They improve technical coverage, but do
not replace adjudicated gold labels or an independent external test.

## Ile Alatau paired glacier cohort

The 2024 cohort contains 18 RGI glacier IDs, stratified across small, medium,
and large inventory area classes. The compact S2+terrain control and the
S2+terrain+S1 model are evaluated on the same glacier crops, then compared with
a glacier-level paired bootstrap (1,000 resamples, seed 42).

| Candidate minus control | Estimate | 95% CI |
| --- | ---: | ---: |
| Hard Dice | +0.0352 | +0.0161 to +0.0541 |
| Hard IoU | +0.0257 | +0.0109 to +0.0409 |
| Recall | −0.1413 | −0.2271 to −0.0708 |
| Absolute area error | −0.8363 km² | −1.1252 to −0.5835 km² |

This is **post-hoc and non-independent**: the models and pseudo-labels both
derive from the same RGI-based project context. It is a paired diagnostic, not
a holdout accuracy claim.

## Provisional external-geography stress test

Nine glacier crops were selected by a documented broad 79.0–84.1°E,
43.0–45.37°N candidate filter, downloaded from Google Earth Engine for summer
2024 (Sentinel-2 SR plus SRTM terrain), and checked with SHA-256. The filter is
not an authoritative Zhetysu boundary; the result is an external-geography
stress test only.

The S2+terrain model obtained mean hard Dice 0.1815 (95% CI 0.0692–0.3305) and
mean area-error percentage 1373.0%. This poor, uncertain result is useful: it
demonstrates that the current model cannot claim external generalisation and
that RGI-2000 pseudo-labels are insufficient for a 2024 external validation.

## Files and gate

- `benchmarks/v2/provisional/ile_alatau_rgi_2024_per_glacier.csv`
- `benchmarks/v2/provisional/ile_alatau_rgi_2024_paired_summary.json`
- `benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_per_glacier.csv`
- `benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_summary.json`

Run `python scripts/validate_provisional_cohorts.py` to verify tables and raw
external source checksums. The strict `validate_benchmark_v2.py` gate continues
to reject gold/external scientific claims until expert adjudication is added.
