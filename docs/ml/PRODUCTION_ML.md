# GlacierNET-KZ production ML contract

## What is deployable now

The primary runtime model is `temporal_s2_terrain_s1`. Its input order is
fixed and machine-readable:

1. Sentinel-2 B2, B3, B4, B8, B8A, B11, B12;
2. NDSI, NDWI, BSI, EVI;
3. normalized elevation, slope and aspect;
4. normalized Sentinel-1 VV and VH.

The API verifies the SavedModel SHA-256 before deserialization, reads the
decision threshold from the versioned validation report, checks the model
signature against the 16-channel schema, and returns the schema, threshold,
inference variant and uncertainty caveats with every result.

For a georeferenced 7-band Sentinel-2 GeoTIFF, the API computes the four
indices and reprojects the local terrain and year-matched SAR composite to the
uploaded grid. For a prebuilt 14/16-channel input, values must already follow
the canonical normalized order. Missing modalities are never silently filled
with invented values.

## Evidence hierarchy

Current positive evidence:

- one-AOI temporal holdout with 2024 untouched during training and threshold
  calibration;
- validation-only threshold selection;
- compact paired optical/terrain versus optical/terrain/SAR ablation;
- trusted local SavedModel artifacts;
- patch overlap, area, calibration and diagnostic boundary metrics;
- glacier-level provisional paired analysis.

Current hard limits:

- RGI-derived masks are silver labels, not independent expert gold labels;
- the Zhetysu cohort is provisional and currently demonstrates a severe
  cross-region generalization gap;
- patch boundary diagnostics are not substitutes for non-overlapping
  glacier-level HD95/ASSD;
- predictive entropy and MC dropout are uncertainty indicators, not calibrated
  hazard probabilities.

No code change can honestly remove those limits without independent labels and
an authoritative external test cohort.

## Reproducible commands

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/validate_trusted_models.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/benchmark_inference_variants.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/evaluate_temporal_benchmark.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  -m src.train \
  --patches-dir data/processed/patches/sentinel2_terrain_s1_year_holdout_2017_2024 \
  --model unet \
  --seed 42
```

`--modality-dropout 0.1` is available as an experimental robustness variant.
It is deliberately off by default until it beats the same validation protocol.
Interrupted training resumes from a Keras backup, deterministic operations are
requested, NaN terminates the run, and a provenance JSON records the dataset
manifest digest, split sizes, feature schema, seed and hyperparameters.

## Research-driven next experiments

The implemented order is intentional:

1. establish an operational and reproducible multimodal baseline;
2. add glacier/spatial external labels and failure cohorts;
3. compare boundary-supervised heads or HED-UNet against that baseline;
4. compare domain-generalization pretraining such as CrossEarth/AnySat only
   under the same external protocol;
5. promote a larger model only when validation improvement survives the
   untouched external test and its runtime budget.

Primary references and official implementations:

- [Multi-Sensor Deep Learning for Glacier Mapping](https://arxiv.org/abs/2409.12034)
- [HED-UNet paper](https://mediatum.ub.tum.de/doc/1772130/document.pdf) and
  [official code](https://github.com/khdlr/HED-UNet)
- [CrossEarth paper](https://arxiv.org/abs/2410.22629) and
  [official code](https://github.com/cuzyoung/crossearth)
- [Uncertainty evaluation of segmentation models for Earth observation](https://arxiv.org/abs/2510.19586)
- [VALUES uncertainty validation framework](https://github.com/IML-DKFZ/values)
- [AnySat official implementation](https://github.com/gastruc/AnySat)

These projects are research candidates, not borrowed accuracy claims. A
foundation model is not called “better” for GlacierNET-KZ until it wins the
local validation protocol and the external glacier-level gate.
