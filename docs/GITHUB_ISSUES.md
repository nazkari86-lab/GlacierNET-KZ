# GitHub Issues for GlacierNET-KZ

Copy these issues to GitHub using `gh issue create` or manually.

---

## Issue 1: Multi-Year U-Net Training

**Title:** `[ml] Train U-Net on multi-year data (2016-2020) to improve cross-sensor generalization`

**Labels:** `enhancement`, `ml`, `good first issue`

**Description:**
Currently U-Net is trained only on 2020 Sentinel-2 data, limiting its generalization to other years and sensors (Landsat).

### Task
- Extend `src/preprocessing.py` to load patches from multiple years (2016, 2017, 2020)
- Modify `src/models.py` U-Net training to accept multi-year data
- Train and compare F1/IoU against the single-year baseline (F1=0.876)

### Acceptance Criteria
- [ ] U-Net trained on 2016+2017+2020 data
- [ ] F1 >= 0.88 on test set
- [ ] Model saved as `models/unet_multiyear_best.h5`
- [ ] Results added to `results/tables/model_comparison.csv`

### Resources
- `notebooks/04_unet_training.ipynb` — current single-year training
- `data/processed/patches/` — existing patches for 2020
- Paul et al. (2020) — multi-year training strategies for glacier mapping

---

## Issue 2: Landsat Preprocessing Pipeline

**Title:** `[data] Build automated Landsat preprocessing pipeline for 2000-2013`

**Labels:** `data`, `enhancement`

**Description:**
Landsat data (2000–2013) requires preprocessing to match Sentinel-2 band structure for consistent model input.

### Task
- Create `src/landsat_preprocessing.py` with:
  - Atmospheric correction (if needed)
  - Cloud masking (QA_PIXEL band)
  - Resampling to 10m (if using pansharpened)
  - Band alignment to match Sentinel-2 channels
- Update `src/data_loader.py` to handle Landsat-specific loading
- Validate on 2010 Landsat scene

### Acceptance Criteria
- [ ] Landsat scenes preprocessed for all 6 years (2000, 2003, 2005, 2008, 2010, 2013)
- [ ] Output format matches Sentinel-2 processed data
- [ ] Cloud coverage < 10% per composite
- [ ] Unit tests for Landsat-specific functions

### Resources
- `notebooks/01_data_download.ipynb` — GEE download scripts
- USGS Landsat Collection 2 documentation

---

## Issue 3: Web Dashboard with Interactive Maps

**Title:** `[web] Build Gradio/Streamlit dashboard for interactive glacier visualization`

**Labels:** `web`, `enhancement`, `good first issue`

**Description:**
Create an interactive web dashboard to visualize glacier classification results across years.

### Task
- Build a Gradio or Streamlit app with:
  - Year selector (2000–2020)
  - Method selector (U-Net, RF, NDSI)
  - Interactive map with overlay (Leaflet or Folium)
  - Statistics panel (area, trend, confidence)
  - Model comparison chart
- Deploy to HuggingFace Spaces

### Acceptance Criteria
- [ ] App loads all 9 years of results
- [ ] Interactive map with glacier overlay
- [ ] Method comparison view
- [ ] Deployed to HuggingFace Spaces
- [ ] README with screenshots

### Resources
- `results/figures/` — existing static plots
- `results/tables/` — CSV data for charts
- `spaces/` — deployment template

---

## Issue 4: WGMS Validation Against Tuyuksu Glacier

**Title:** `[validation] Compare predictions with WGMS reference data for Tuyuksu`

**Labels:** `science`, `validation`

**Description:**
Validate satellite-derived glacier areas against WGMS Fluctuations of Glaciers database for Tuyuksu glacier (WGMS ID: 817).

### Task
1. Download WGMS FoG database: https://doi.org/10.5904/wgms-fog-2026-02-10 (868 MB)
2. Filter for Tuyuksu (WGMS ID: 817)
3. Extract annual area measurements (1957–present)
4. Run `rmse_against_wgms()` from `src/metrics.py`
5. Create comparison plot (our RF vs WGMS)
6. Compute RMSE, bias, R²

### Acceptance Criteria
- [ ] WGMS data downloaded and filtered
- [ ] RMSE < 0.5 km² for overlapping years
- [ ] Bias < 10% of mean glacier area
- [ ] Comparison plot saved to `results/figures/wgms_validation.png`
- [ ] Results documented in paper Section 4.6

### Resources
- `src/metrics.py:101+` — `rmse_against_wgms()` implementation
- `notebooks/05_temporal_analysis.ipynb` — WGMS comparison placeholder
- Khromova et al. (2019) — Tuyuksu area time series

---

## Issue 5: Ensemble Model with Uncertainty Quantification

**Title:** `[ml] Build ensemble model combining U-Net + RF + NDSI with uncertainty`

**Labels:** `ml`, `enhancement`

**Description:**
Create an ensemble that combines all three methods with uncertainty quantification for production deployment.

### Task
- Implement weighted ensemble in `src/models.py`:
  - Weight by per-method F1 scores
  - Add MC-Dropout for U-Net uncertainty (T=10)
  - Combine with RF probability output
  - NDSI as binary prior
- Create uncertainty maps showing prediction confidence
- Add ensemble metrics to comparison table

### Acceptance Criteria
- [ ] Ensemble F1 >= 0.88 (better than individual methods)
- [ ] Uncertainty maps for each year saved to `results/figures/uncertainty/`
- [ ] Ensemble results in `results/tables/ensemble_results.csv`
- [ ] Paper Section 4.8 updated with ensemble results

### Resources
- `src/models.py` — existing U-Net, RF, NDSI implementations
- `src/config.py` — MC_DROPOUT_PROB, TTA_ENABLED constants
- Gal & Ghahramani (2016) — MC-Dropout theory
- Lakshminarayanan et al. (2017) — deep ensembles
