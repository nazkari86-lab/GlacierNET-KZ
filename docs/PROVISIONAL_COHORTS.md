# Automatic Provisional Cohorts

These cohorts were produced automatically from locally available RGI 7.0
polygons and satellite/terrain data. They improve technical coverage, but do
not replace adjudicated gold labels or an independent external test.

## Ile Alatau paired glacier cohort

The 2024 cohort contains 18 unique RGI glacier IDs, stratified across small,
medium, and large inventory area classes. The compact S2+terrain control and
the S2+terrain+S1 model are evaluated on the same glacier crops, then compared
with a glacier-level paired bootstrap (1,000 resamples, seed 42), a two-sided
paired Wilcoxon test, and candidate win rates.

| Candidate minus control | Estimate | 95% CI | Wilcoxon p | Candidate win rate |
| --- | ---: | ---: | ---: | ---: |
| Hard Dice | +0.0352 | +0.0161 to +0.0541 | 0.00105 | 83.3% |
| Hard IoU | +0.0257 | +0.0109 to +0.0409 | 0.00105 | 83.3% |
| Precision | +0.0294 | +0.0120 to +0.0489 | 0.00105 | 83.3% |
| Recall | −0.1413 | −0.2271 to −0.0708 | 0.00003 | 5.6% |
| Absolute area error | −0.8363 km² | −1.1252 to −0.5835 km² | 0.00001 | 100.0% |

This is **post-hoc and non-independent**: the models and pseudo-labels both
derive from the same RGI-based project context. It is a paired diagnostic, not
a holdout accuracy claim. The table also persists TP/FP/FN/TN counts, true and
predicted area, and HD95/ASSD boundary distances. Unbounded boundary distances
are represented explicitly rather than silently dropped.

## Provisional external-geography stress test

Nine unique glacier crops were selected by a documented broad 79.0–84.1°E,
43.0–45.37°N candidate filter and downloaded from Google Earth Engine for
summer 2024 (Sentinel-2 SR plus SRTM terrain). Downloads use an atomic
`.part`-then-rename workflow. Each source record freezes its eligible scene
IDs, cloud percentages, date and collection rules, SHA-256, band count, CRS,
pixel size, dimensions and bounds. Model, RGI and output-table hashes are also
recorded. The filter is not an authoritative Zhetysu boundary; the result is an
external-geography stress test only.

The S2+terrain model obtained mean hard Dice 0.1815 (95% CI 0.0692–0.3305) and
mean area-error percentage 1373.0%. This poor, uncertain result is useful: it
demonstrates that the current model cannot claim external generalisation and
that RGI-2000 pseudo-labels are insufficient for a 2024 external validation.

## Generalisation Sentinel: inventory-guided failure containment

The unconstrained external prediction exposed a practical failure mode: summer
snow elsewhere in the downloaded crop can be mapped as part of the target
glacier. A frozen decoder now combines NDSI evidence with a 100 m search buffer
around the historical inventory and retains only spectral components connected
to that inventory. The threshold and buffer were selected on the 18-glacier Ile
Alatau cohort, then frozen before the external replay.

On the same nine-glacier provisional replay, mean hard Dice increased to 0.5433
(95% CI 0.3957–0.6593), while mean absolute area error fell to 51.9%. The paired
Dice delta was +0.3618 (95% CI +0.2127 to +0.5011); the paired absolute area
error delta was −1321.2 percentage points (95% CI −2261.2 to −547.4).

This does **not** repair the independent external-generalisation gate. RGI is
used as the search prior and as the provisional comparison mask, so the result
measures failure containment and inventory consistency—not independent
current-boundary accuracy. It is intended for candidate generation,
annotation prioritisation and explicit abstention.

## Files and gate

- `benchmarks/v2/provisional/ile_alatau_rgi_2024_per_glacier.csv`
- `benchmarks/v2/provisional/ile_alatau_rgi_2024_paired_summary.json`
- `benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_per_glacier.csv`
- `benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_summary.json`
- `benchmarks/v2/provisional/inventory_guided_decoder_2024.json`
- `benchmarks/v2/provisional/inventory_guided_decoder_zhetysu_2024_per_glacier.csv`
- `benchmarks/v2/claims_registry.json`

Run `python scripts/validate_provisional_cohorts.py` to verify tables and raw
external source checksums, spatial metadata, scene provenance and cohort
cardinality. Run `python scripts/validate_claims_registry.py` to verify that
every major scientific claim is tied to evidence and an allowed status. The
strict `validate_benchmark_v2.py` gate continues to reject gold/external
scientific claims until expert adjudication is added.
