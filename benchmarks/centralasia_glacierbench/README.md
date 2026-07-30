# CentralAsia-GlacierBench

CentralAsia-GlacierBench is GlacierNET-KZ's reproducible, evidence-bound
evaluation suite. It reports track-level results instead of a single composite
score so that a strong silver-label segmentation result cannot hide missing
physical or event validation.

## Tracks

1. Temporal segmentation: untouched 2024 test year.
2. Sentinel-1 + Sentinel-2 multimodal ablation on the same one-AOI split,
   labels and training setup as its control.
3. Frozen cross-region transfer: Ile Alatau calibration and Zhetysu replay,
   with glacier-level bootstrap confidence intervals.
4. Official GlaViTU transfer: frozen HMA and global checkpoints on the same
   Zhetysu replay, including the honest negative result.
5. External lake segmentation: Cryo-Bench GLD frozen test.
6. ITS_LIVE motion reference: real point time series at selected RGI7 glacier
   centroids.
7. Physical reference: Hugonnet RGI-13 mass change. No RGI6-to-RGI7 join is
   fabricated.
8. HMA lake-terminating reference: observed 1990-2022 glacier and lake area
   changes in three Central Asian mountain systems.
9. Retrospective event co-location: HMAGLOFDB coordinates screened against HMA
   glacier geometries at 1/2/5/10 km. Proximity is not presented as causality
   or a calibrated warning.
10. Active Evidence Acquisition readiness: performance remains blocked until
    source-reviewed events, verified controls, immutable pre-event snapshots
    and realised observation-value rows are all present.

## Reproduce

```bash
python scripts/sync_centralasia_glacierbench.py
python scripts/build_centralasia_glacierbench.py
```

The first command resumes interrupted downloads and verifies publisher
checksums when available. The second writes
`current/report.json`, including hashes for every measured local result.

To execute every locally feasible real-data track in one command:

```bash
python scripts/run_centralasia_glacierbench.py --full
```

The full runner trains a deterministic lightweight GLD baseline, evaluates the
official GlaViTU HMA checkpoint on the frozen Zhetysu replay, materialises
ITS_LIVE point time series, and rebuilds the evidence report.

`protocol.json` is the scientific contract. A source marked local is not
automatically a measured track, and missing evidence never becomes a synthetic
score.

The compact profile currently supports five model-evaluation tracks and four
separate reference-evidence tracks. Cryo-Bench
GLID and GSDD remain optional large sources and require an explicit
`--include-large` flag plus the disk safety margin; their absence is shown in
the report source ledger rather than hidden behind a green track count.
