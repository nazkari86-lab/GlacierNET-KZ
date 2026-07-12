# GlacierNET-KZ Improvement Plan — 2026-06-28

## Current Audit Snapshot

- Core Python tests: `411 passed`.
- API/experimental tests: `419 passed, 2 skipped`.
- Web unit tests: `170 passed`.
- Web production build: passed.
- Changed Python files pass `ruff check`.
- Existing GeoTIFFs open with `rasterio` and share `EPSG:32642`, shape `5228 x 8583`.
- Raw data baseline is complete locally:
  - Sentinel-2: `2015–2024`
  - Landsat: `2000, 2003, 2005, 2008, 2010, 2013`
- `scripts/validate_data_quality.py` passes and writes `results/data_quality_report.json`.
- `scripts/build_data_inventory.py` writes 16 raster rows to `results/tables/data_inventory.csv`.

## Fixes Applied In This Pass

- Fixed compact Sentinel-2 export path:
  - `src.data_loader.get_sentinel2()` already creates 7-band `uint16` reflectance composites.
  - `src.data_loader.export_year_to_drive()` now preserves the image dtype instead of forcing `.toFloat()`.
  - `scripts/download_all_missing.py` no longer adds NDSI/NDWI/BSI/EVI before Sentinel-2 export.
  - Local `load_image()` still restores the expected 11-channel interface by deriving indices locally.
- Added `tests/test_data_loader_export.py` to prevent future regressions that inflate Drive exports.
- Fixed Keras 3 compatibility in experimental modules:
  - `src/graph_neural_network.py`
  - `src/multi_task_learning.py`
  - `src/vision_transformer.py`
- Synced project docs with current files:
  - Raw Sentinel-2 files now exist for `2015–2024`.
  - `sentinel2_2015.tif` is documented as a late-2015 annual TOA fallback because no summer L2A/SR scenes exist for the AOI.
  - `models/unet_plus_plus_best.h5` exists and is no longer a missing artifact.
  - `results/pipeline_status.json` regenerated from disk.
- Added machine-readable data quality/provenance support:
  - `scripts/validate_data_quality.py`
  - `scripts/build_data_inventory.py`
  - refreshed `results/stac/catalog.json`

## Remaining Issues

1. Training data coverage:
   - Raw and prediction coverage spans all target years.
   - Yearly Sentinel-2 training masks now exist and validate for `2016–2024`.
   - Patch arrays exist for `2020`; validated limited samples exist for `2021` and capped `2016–2024` under `data/processed/patches/`.
   - A 1-epoch U-Net smoke training run on capped `2016–2024` completed successfully; saved models are smoke artifacts, not production-quality weights.
   - A year-held-out manifest now assigns `2016–2022` to train, `2023` to validation and `2024` to test without copying arrays. The preliminary 5-epoch focal-loss run did not converge on the held-out validation year (recall remained `0`), so no temporal performance claim or model artifact is retained.
   - A larger temporally separated sample is now available: 2,304 patches across
     2016–2024 (256 per year), 14 channels (11 Sentinel-2-derived + elevation,
     slope and aspect), with `2016–2022/2023/2024` split. A 12-epoch focal U-Net
     benchmark reached untouched-2024 `Dice=0.7802`, `IoU=0.7382`, precision
     `0.9712`, and recall `0.7547`; the machine-readable protocol/result is
     `results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json`.
     This is temporal validation in one AOI against RGI-derived masks, not an
     external field-validation or cross-region generalization claim.
   - Sentinel-1 2017–2024 summer composites have been submitted to the Earth
     Engine export queue. They are not a local/model input until the verified
     download helper records them as `downloaded` in the export manifest.

2. Large raster footprint:
   - Current Sentinel-2/Landsat exports are mostly `float32` and often 600 MB to 1.3 GB each.
   - Future Sentinel-2 exports should stay compact 7-band `uint16`; indices should remain local derived features.

3. 2015 Sentinel-2 caveat:
   - `sentinel2_2015.tif` is usable as a documented fallback, but it is not a summer L2A/SR composite.
   - International reporting should mark 2015 separately or exclude it from strict summer Sentinel-2 model benchmarking.

4. Frontend warnings:
   - `npm run lint` passes with warnings, mostly unused imports/vars.
   - `npm run build` warns about workspace root because lockfiles exist above `glacierkz-web`.
   - Build also warns that one Recharts container has invalid width/height during prerender.

5. Dependency horizon:
   - Google API libraries warn that Python 3.10 support ends after 2026-10-04.
   - Keep the ML env on Python 3.10 for TensorFlow compatibility now, but plan a Python 3.11 migration test.

## Priority Plan

### P0 — Reproducible Data Baseline

- Keep `scripts/validate_data_quality.py`, `scripts/build_data_inventory.py`, and `scripts/export_stac_catalog.py` as required gates after every data change.
- Rebuild masks/patches for every reliable Sentinel year or clearly document that supervised training uses only 2020. **Masks done:** `scripts/build_year_masks.py` generated `data/processed/masks/mask_2016.tif` through `mask_2024.tif`; `scripts/validate_training_masks.py` validates them against source rasters and manifest.
- Add a one-command provenance check to CI/lightweight local QA. **Done:** `scripts/validate_decision_readiness.py` now checks raw sources, source flags, 2015 strict-trend exclusion, model references, git/snapshot IDs, and summary/table consistency.
- Add a patch-manifest gate for generated multi-year patch datasets. **Done:** `scripts/validate_patch_manifest.py` validates array shapes/counts, source/mask paths, 2015 exclusion, and random-split leakage warnings; capped `2016–2024` sample validates.
- Add a temporal split without random-patch leakage. **Done:** `scripts/build_year_holdout_manifest.py` and `src.train` load every patch from each year into one exclusive split; the validator checks exact, non-overlapping year coverage.
- Add reproducible real-data EDA and RF interpretability artifacts. **Done:** `scripts/build_real_data_eda.py` and `scripts/analyze_rf_feature_importance.py` write the figure/table artifacts and run from the evidence package.

### P1 — Scientific Consistency

- Recompute `results/tables/glacier_areas_all_years.csv` after raw 2020 is restored.
- Add provenance columns to result CSVs: `source_file`, `model_file`, `created_at`, `git_or_snapshot_id`. **Done for decision-ready time series:** `results/tables/decision_ready_area_timeseries.csv`.
- Add a validation script that fails if a year appears in `predictions/` but has no raw source file or documented exception. **Done:** `scripts/validate_data_coverage.py` and `scripts/validate_decision_readiness.py`.
- Add 95% CI/p-value reporting to every trend table used in papers/posters.
- Add explicit data-source flags: `landsat_historical`, `sentinel2_sr`, `sentinel2_toa_fallback`.

### P2 — Product/API Cleanup

- Fix frontend lint warnings by removing unused imports/state.
- Set explicit `turbopack.root` in `glacierkz-web/next.config.*` to silence workspace-root ambiguity.
- Fix the Recharts prerender warning by giving affected chart containers stable min dimensions.

### P3 — Maintenance

- Decide whether experimental ML modules are production, optional, or research-only.
- Keep experimental modules covered by tests, but mark long/heavy training tests separately.
- Test Python 3.11 environment before Google API Python 3.10 deprecation becomes urgent.
