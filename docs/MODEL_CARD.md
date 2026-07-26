# GlacierNET-KZ Benchmark Models — Model Card

## Intended use

These TensorFlow SavedModels support reproducible glacier-segmentation research
and controlled feature ablations over the Ile Alatau study AOI. They may be
used to reproduce Benchmark v2 results, inspect errors, and generate candidate
masks for expert review.

They are not validated for official inventory updates, emergency warnings,
autonomous infrastructure decisions, or unsupervised use outside the study
distribution.

## Models and verified test metrics

| Model | Inputs | Threshold | Hard Dice | Hard IoU | Area error |
| --- | --- | ---: | ---: | ---: | ---: |
| S2 + terrain | 14 channels | 0.2 | 0.8746 | 0.7771 | −49.8204 km² |
| Compact control | S2 + terrain | 0.3 | 0.8937 | 0.8078 | −4.7873 km² |
| Compact S1 | control + S1 VV/VH | 0.5 | 0.9036 | 0.8242 | −3.6214 km² |

Thresholds were selected from validation data and frozen before the 2024 test.
The labels are RGI-derived silver labels, not independently drawn gold labels.
Exact precision, recall, split, calibration, input provenance, and artifact
digests are in the corresponding JSON reports and
`releases/model_artifacts.v1.json`.

## Training and evaluation

- Fixed year-disjoint train/validation/test manifests.
- Fixed random seeds where supported by the training stack.
- Test-set metrics use one hard binary mask per model.
- The compact control and Sentinel-1 model use the same patches, labels,
  splits, and training protocol; model-specific thresholds are calibrated on
  validation data.
- Model directories are accepted only when their deterministic directory hash
  matches `models/trusted_artifacts.json`.

## Known limitations

- One AOI and one temporal test year.
- Inventory-derived labels may contain stale or uncertain boundaries.
- No glacier-aware IDs in current arrays, so glacier-level bootstrap intervals,
  boundary F1, Hausdorff95, and ASSD are still blocked.
- No independent Zhetysu Alatau test set or field validation.
- Cloud, seasonal snow, shadows, debris-covered ice, and sensor differences can
  produce systematic errors.
- Output probabilities are segmentation scores, not calibrated hazard
  probabilities.

## Human oversight

Inspect source imagery, scene quality, uncertainty, and georeferencing before
accepting a mask. Scientific publication requires the gold-label and external
test gates in `benchmarks/v2`; operational decisions require independent domain
review beyond this repository.

## Artifact publication

Run `python scripts/build_model_release_manifest.py` before packaging. Release
archives must preserve the SavedModel directory, include the generated
manifest, publish archive SHA-256 values, and be downloaded once for independent
verification. A GitHub asset is not a DOI; the DOI field remains null until an
external repository such as Zenodo actually mints one.
