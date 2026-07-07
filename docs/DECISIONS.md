# Architectural Decisions — GlacierNET-KZ

All significant design choices recorded here with context, alternatives considered, and rationale.

---

## D-001: Primary Classification Method — Random Forest for Time Series

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Need a single method that works across all 9 years (2000–2020). U-Net trained only on 2020 Sentinel-2 data cannot generalize to Landsat sensors without retraining. NDSI thresholding only works for years with visible bands.

**Decision:** Use Random Forest as the primary method for the full temporal analysis (2000–2020).

**Alternatives considered:**
- U-Net: Best F1 (0.876) but trained only on 2020 Sentinel-2; transfer to Landsat unvalidated
- NDSI: Simple, interpretable, but only available for 4 of 9 years
- Ensemble: Would improve accuracy but adds complexity; no clear consensus on weighting

**Rationale:** RF uses all 11 spectral channels, works with both Landsat and Sentinel-2, and is available for every year. F1 (0.853) is within 2.3 pp of U-Net.

**Consequences:**
- Time series has 9 data points (RF) instead of 4 (NDSI)
- Cross-sensor inconsistency remains (Landsat 30m vs Sentinel-2 10m)
- 2003 outlier (726.56 km²) likely cloud contamination inflating RF classification

---

## D-002: Linear Forecast Model

**Date:** 2026-06-26  
**Status:** Accepted with caveats  
**Context:** Need to project glacier area to 2050 for water resource impact assessment.

**Decision:** Use ordinary least squares (OLS) linear regression for the 2050 forecast.

**Alternatives considered:**
- Exponential decay: More physically realistic but poor fit with current data variability
- Polynomial (degree 2): Overfits the inter-annual noise
- ARIMA: Requires more data points; 9 years is marginal
- Machine learning forecast (LSTM): Overkill for 9 data points

**Rationale:** Linear model is transparent, reproducible, and the simplest model consistent with the data. Slope = −12.66 km²/yr is meaningful despite R² = 0.54.

**Consequences:**
- 95% CI widens significantly after 2030 (uncertainty acknowledged in paper)
- 2003 outlier inflates residual variance, widening CI
- Forecast is a scenario, not a prediction — stated clearly in paper

---

## D-003: U-Net Architecture — Attention U-Net

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Choose U-Net variant for semantic segmentation benchmark.

**Decision:** Use Attention U-Net as the deep learning baseline.

**Alternatives considered:**
- Vanilla U-Net: Simpler, but attention gates improve small glacier detection
- U-Net++: Better for small objects but more parameters, harder to train on limited data
- DeepLabv3+: Atrous convolution good for large-scale features, less tested on glacier data

**Rationale:** Attention gates (Oktay et al., 2018) help the model focus on glacier boundaries. Filters [32, 64, 128, 256] give ~31M parameters — appropriate for single-year training.

**Consequences:**
- Model trained on 2020 Sentinel-2 only (single year, single sensor)
- `attention_unet_best.h5` weights file is missing from repo — must be regenerated
- TTA (3 flips) adds ~3x inference time but improves F1 by ~1–2 pp

---

## D-004: Patch-Based Training Strategy

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Full Sentinel-2 scene is ~1.5 GB — too large for GPU memory.

**Decision:** Extract 256×256 patches with 50% stride, filtering patches with <1% glacier fraction.

**Alternatives considered:**
- Random crops: Faster but may miss small glaciers
- Sliding window with overlap (50%): Chosen — balances coverage and redundancy
- Multi-scale: Pyramidal approach adds complexity; 256px at 10m = 2.56 km² per patch

**Rationale:** 256×256 is standard for U-Net. 50% stride ensures no glacier patch is missed. `BACKGROUND_KEEP_PROB = 0.30` prevents class imbalance from overwhelming training.

**Consequences:**
- ~200–400 patches per year (varies with glacier extent)
- Patch extraction is I/O bound — benefits from SSD
- Border artifacts between patches handled by overlap averaging during inference

---

## D-005: Spectral Feature Engineering

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Which spectral channels and indices to feed into models.

**Decision:** Use 11 channels: 7 Sentinel-2 bands (B2, B3, B4, B8, B8A, B11, B12) + 4 indices (NDSI, NDWI, BSI, EVI).

**Alternatives considered:**
- Raw bands only: Misses domain-specific information (NDSI is critical for snow/ice)
- Full band set (13 bands): B1, B9, B10 are atmospheric — not useful for surface classification
- Custom indices: NDGI, NDMI tested in literature but marginal improvement over NDSI/NDWI

**Rationale:** NDSI is the gold standard for glacier mapping. NDWI helps with water bodies. BSI distinguishes bare soil from ice. EVI improves vegetation discrimination.

**Consequences:**
- NDSI threshold (0.4) used as baseline — comparable to literature (Paul et al., 2013)
- All indices computed per-pixel before training — no runtime cost during inference
- `BAND_INDEX` dict in config.py enforces consistent ordering across pipeline

---

## D-006: Study Area Bounding Box

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Define spatial extent for reproducibility.

**Decision:** Bounding box: 76.5–77.5°E, 42.8–43.2°N (Ili Alatau, Заилийский Алатау).

**Alternatives considered:**
- Larger box (76–78°E): Includes Zailiysky and Kungey Alatau — more glaciers but longer processing
- Smaller box (77–77.3°E): Only Tuyuksu glacier — too narrow for regional analysis
- Administrative boundary (Almaty Oblast): Mixes glacier and non-glacier terrain

**Rationale:** 76.5–77.5°E covers the main glacierized basin of the Ili Alatau including Tuyuksu, Bogdanovich, and other reference glaciers. 0.4° latitude captures the full glacier elevation range.

**Consequences:**
- Total area: ~44.9 km² (4,487 × 10 m pixels)
- CRS: EPSG:32642 (UTM 42N) for metric analysis
- Excludes Dzungarian Alatau glaciers (different climate regime)

---

## D-007: Training/Validation/Test Split

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Split 2020 patches for model training and evaluation.

**Decision:** 70% train / 15% validation / 15% test, stratified by glacier fraction.

**Alternatives considered:**
- 80/10/10: More training data but less reliable validation
- Spatial split (different geographic regions): Better generalization test but reduces training set
- Temporal split (train on other years): Not applicable — only 2020 has patches

**Rationale:** Standard split for deep learning. Stratification ensures all splits have representative glacier coverage. Early stopping uses validation set; test set is held out for final metrics.

**Consequences:**
- ~140 train / ~30 val / ~30 test patches
- Single-year training limits transferability (acknowledged in Discussion)
- Random seed (42) ensures reproducibility

---

## D-008: Uncertainty Quantification Method

**Date:** 2026-06-26  
**Status:** Accepted  
**Context:** Need to quantify prediction confidence for ensemble outputs.

**Decision:** Use MC-Dropout (Gal & Ghahramani, 2016) with T=10 forward passes for U-Net uncertainty.

**Alternatives considered:**
- Deep ensembles (train 5 models): More accurate but 5x compute cost
- Bayesian Neural Networks: Theoretically ideal but impractical with current TF
- Simple thresholding on probability: No uncertainty estimate, just hard classification
- Conformal prediction: Distribution-free but requires calibration set

**Rationale:** MC-Dropout reuses existing dropout layers during inference — no retraining needed. T=10 passes give stable uncertainty estimates. Combined with TTA (3 flips) for 30 total forward passes.

**Consequences:**
- Inference time: ~30x single pass (manageable for 9 years)
- `TTA_ENABLED = True`, `CRF_ENABLED = False` in config.py
- Uncertainty maps saved alongside binary masks for downstream analysis

---

## D-009: WGMS Validation Strategy

**Date:** 2026-06-26  
**Status:** Partially blocked  
**Context:** Validate satellite-derived areas against ground-truth WGMS reference data.

**Decision:** Compare against WGMS FoG database for Tuyuksu glacier (WGMS ID: 817).

**Alternatives considered:**
- RGI v7.0 outlines: Available but static (year 2000 only)
- Manual digitization: Authoritative but labor-intensive and subjective
- Landsat-based comparison with published studies: Indirect but feasible

**Rationale:** Tuyuksu is a WGMS reference glacier with observations since 1957. Direct comparison provides strongest validation.

**Consequences:**
- WGMS FoG database requires manual download (868 MB, DOI: 10.5904/wgms-fog-2026-02-10)
- API endpoints return 404 — database is not available programmatically
- `rmse_against_wgms()` function in `src/metrics.py` is implemented but awaits data
- Fallback: Compare with published area estimates from Khromova et al. (2019) or Bolch et al. (2017)
