# Controlled Sentinel-1 ablation protocol

## Question

Does adding aligned Sentinel-1 VV/VH features improve glacier segmentation over
the existing Sentinel-2 plus terrain input under an otherwise identical compact
temporal experiment?

## Controls

- Candidate: 16 channels — 11 optical/index channels, 3 terrain channels, and
  Sentinel-1 `VV_dB_normalized` / `VH_dB_normalized`.
- Control: the first 14 channels projected from those exact candidate arrays.
- Labels: byte-identical local hardlinks between candidate and control datasets.
- Sampling: 64 patches per year for 2017–2024; the same sampled coordinates and
  split files are used in both arms.
- Temporal split: train 2017–2022, validation 2023, untouched test 2024.
- Training: U-Net, focal loss, 12 epochs, batch size 4, fixed project seed.
- Selection: best checkpoint is selected only by validation Dice; the 2024 test
  set is evaluated after training.

The report builder verifies split equality, feature-prefix lineage, test shape,
label identity, manifest hashes, model hashes, and metric arithmetic. Any
mismatch fails closed.

## Interpretation boundary

This is a compact one-AOI ablation with RGI-derived silver labels. It can answer
whether VV/VH helped in this controlled run. It cannot establish cross-region
generalisation, expert-label accuracy, field accuracy, or operational
superiority. The result does not replace the larger temporal benchmark.

## Leakage policy

ESA WorldCover is retained as contextual metadata only. Its permanent snow/ice
class is derived from optical Earth observation and may act as label-like
information for this task. It must not enter model features until a separate
leakage-controlled experiment defines acquisition dates, spatial independence,
and an evaluation protocol that prevents the map product from encoding the
target.

## Reproduction

```bash
python scripts/validate_patch_manifest.py \
  data/processed/patches/sentinel2_terrain_s1_ablation_2017_2024/manifest.json \
  --require-years 2017-2024
python scripts/validate_year_holdout.py \
  data/processed/patches/sentinel2_terrain_s1_year_holdout_2017_2024/manifest.json
python scripts/validate_ablation_report.py \
  results/ablation_sentinel1_2017_2024.json
```
