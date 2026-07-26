# GlacierNET-KZ Benchmark v2 Protocol

## Scientific question

The primary hypothesis is:

> Adding Sentinel-1 VV/VH to a Sentinel-2 plus terrain model improves glacier
> recall in cloud and terrain-shadow conditions, while potentially increasing
> false positives.

This benchmark tests that hypothesis. It does not claim field accuracy,
Kazakhstan-wide generalisation, or operational readiness.

## Frozen acquisition protocol

Every annual observation must satisfy the same protocol:

```yaml
month_start: 7
month_end: 9
preferred_month: 8
max_cloud_cover_percent: 10
surface_reflectance_only: true
same_aoi: true
same_resolution: true
same_crs: true
same_band_schema: true
```

Selection order is: August first, then minimum cloud, minimum seasonal snow,
minimum haze, and Surface Reflectance rather than TOA. The 2015 TOA fallback is
excluded from strict annual comparison.

Each selected scene requires `image_date`, `sensor`, `product_id`, CRS,
resolution, cloud fraction, shadow fraction, off-glacier snow fraction,
no-data fraction, mean NDSI, high-elevation snow area, source checksum, and a
review decision. Missing acquisition QA prevents an observation from receiving
an accepted status.

## Labels

- Existing RGI-derived masks are **silver labels**.
- Gold labels require two independent annotation passes by the same annotator,
  separated by 5–7 days.
- `intra_annotator_iou` is reported for every glacier-year.
- Disagreements are adjudicated and retained in provenance.
- Clean ice and debris-covered ice are reported separately.

The initial target is 15–25 glaciers, three comparable years, and 45–75
glacier-year observations. Expert review is desirable but is not represented as
completed until a named reviewer signs the dataset card.

## Splits and leakage policy

Three experiments are distinct and must not be merged:

1. Temporal holdout: train 2016–2022, validation 2023, untouched test 2024.
2. Glacier holdout: no `glacier_id` may occur in more than one split.
3. Cross-region: train on Ile Alatau and test on Zhetysu Alatau.

Thresholds and model choices are fixed using validation data only. Test data
must not be used for threshold calibration, early stopping, architecture
selection, or data-quality rule tuning.

## Metrics

All overlap metrics use the same binarised mask:

- Hard Dice and hard IoU
- Precision and recall
- Boundary F1
- Hausdorff distance 95%
- Average symmetric surface distance
- Signed and absolute area error in km²
- Area bias and absolute area error in percent

Results are first computed per glacier. Summary uncertainty uses 1,000
glacier-level bootstrap resamples with a fixed seed and 95% confidence
intervals. Paired model differences are bootstrapped on the same glaciers. If a
confidence interval for a model gain crosses zero, the gain is reported as not
statistically confirmed.

## Threshold calibration

Candidate thresholds are 0.20–0.80 in steps of 0.05. The frozen objective is:

`abs(area_bias_percent) / 100 + (1 - hard_dice)`

The selected validation threshold is recorded before the test set is evaluated.

## Temporal gate

Absolute annual area change is classified as:

| Relative change | Status |
| --- | --- |
| ≤5% | normal |
| >5–15% | review |
| >15–30% | suspicious |
| >30% | reject |

This gate does not assert that rapid physical change is impossible. It prevents
an anomalous estimate from being presented automatically as reliable. A reject
can only be overridden by documented scene QA and manual review.

## Reproducibility

Every report records dataset and model checksums, source commit, random seeds,
split manifest, calibrated threshold, software environment, metric version, and
claims allowed/not allowed. Empty templates are not evidence and must never be
shown as measured results.
