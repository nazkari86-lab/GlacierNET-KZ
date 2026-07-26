# GlacierNET-KZ validation protocol

## Claims we allow

The current 2024 benchmark is a temporal, one-AOI evaluation against
RGI-derived labels. It is useful evidence for a research baseline, but it is
not evidence of cross-region generalisation, field accuracy, or operational
readiness.

Every future benchmark report must declare:

- geographic split: random, spatial, or cross-region;
- temporal split and whether the test years were untouched;
- label provenance and label quality tier;
- model/data/preprocessing versions;
- sample count and glacier-level grouping;
- confidence intervals and area bias;
- all threshold and model-selection decisions made before test evaluation.

## Required benchmark ladder

1. Synthetic smoke test for pipeline mechanics.
2. Random patch split for regression testing only.
3. Year-held-out temporal benchmark.
4. Spatial glacier-held-out benchmark.
5. Cross-region benchmark.
6. Independent expert-labelled gold test set.

Only levels 4–6 support claims about geographic generalisation. Level 6 is
required for publication-grade accuracy claims.

## Required ablation

Report Sentinel-2 only, Sentinel-2 plus terrain, Sentinel-2 plus Sentinel-1,
and the full multimodal model using the same untouched test protocol. Report
per-glacier metrics in addition to pixel averages so large glaciers cannot hide
small-glacier failures.

## Release gate

Before a release, run:

```bash
python scripts/build_data_manifest.py
python scripts/validate_data_manifest.py
python scripts/validate_patch_manifest.py data/processed/patches/sentinel2_year_holdout_2016_2024/manifest.json --require-years 2016-2024
python -m pytest -q --no-cov
```

An offline release must contain regular files, not Google Drive symlinks. When
disk capacity makes that impossible, a linked-data release may use
`--allow-symlinks`, but every target must exist and have a recorded size and
SHA-256. Such a release must state its external data root and is not an
offline/self-contained release.
