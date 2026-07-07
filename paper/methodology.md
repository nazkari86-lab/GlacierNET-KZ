# Methodology — Detailed Technical Description

## 3.1 Study Area

### Geographic Context
- **Region**: Zailiyskiy Alatau (Заилийский Алатау), Northern Tian Shan
- **Bounding Box**: 76.5°E–77.5°E, 42.8°N–43.2°N (UTM Zone 42N)
- **Elevation Range**: 2,200–4,500 m a.s.l.
- **Climate**: Continental, dry summers; mean annual precipitation 500–800 mm (snow-dominated >3000m)

### Target Glaciers

| Glacier | RGI ID | Area (2000) | Type | Notes |
|---------|--------|-------------|------|-------|
| Tuyuksu (Горный) | RGI2000-v7.0-G-13-33843 | ~2.5 km² | Valley, debris-covered snout | WGMS reference since 1957 |
| Bogdanovich | RGI2000-v7.0-G-13-33845 | ~4.1 km² | Valley, clean-ice | Well-studied, accessible |
| Mutny | — (TBD) | ~1.8 km² | Cirque | DJA, coordinates approximate |

### Justification
Zailiyskiy Alatau glaciers have:
1. **Long observation history** (Tuyuksu since 1957 — 67 years of WGMS data)
2. **Proximity to Almaty** (2.5M population dependent on glacial meltwater)
3. **Rapid retreat** (49% volume loss since mid-20th century per UNEP)

---

## 3.2 Data Sources

### 3.2.1 Sentinel-2 MSI (2015–2024)
- **Collection**: `COPERNICUS/S2_SR_HARMONIZED` (Surface Reflectance, harmonized)
- **Spatial Resolution**: 10m (B2,B3,B4,B8), 20m (B8A,B11,B12) → resampled to 10m
- **Temporal Coverage**: 2015–2024 (10 years)
- **Compositing**: Cloud-free summer median composite (July–September)
- **Cloud Masking**: QA60 band + SCL classifier (removes clouds, cirrus, cloud shadows)

**Bands Used** (7 spectral + 4 indices = 11 channels):

| Index | Band(s) | Formula | Purpose |
|-------|---------|---------|---------|
| B2 | Blue | — | Snow/cloud discrimination |
| B3 | Green | — | NDSI input |
| B4 | Red | — | Vegetation indices |
| B8 | NIR | — | NDWI input |
| B8A | NIR narrow | — | Red edge vegetation |
| B11 | SWIR | — | Snow/ice discrimination |
| B12 | SWIR2 | — | Cloud/shadow mask |
| NDSI | B3, B11 | (B3−B11)/(B3+B11) | Snow/ice index (primary) |
| NDWI | B3, B8 | (B3−B8)/(B3+B8) | Water body index |
| BSI | B4, B8, B11, B2 | ((B11+B4)−(B8+B2))/((B11+B4)+(B8+B2)) | Bare soil index |
| EVI | B2, B4, B8 | 2.5×(B8−B4)/(B8+6×B4−7.5×B2+1) | Enhanced vegetation index |

### 3.2.2 Landsat Collection 2 (2000–2013)
- **Collection**: `LANDSAT/LC08/C02/T1_L2` (Landsat 8), `LE07/C02/T1_L2` (Landsat 7)
- **Spatial Resolution**: 30m (resampled to 10m for model compatibility)
- **Gap**: 2014 missing (Landsat 7 SLC-off, Landsat 8 launched Feb 2013)
- **Note**: Cross-calibration coefficients applied (Roy et al. 2016)

### 3.2.3 RGI 7.0 — Ground Truth
- **Source**: Randolph Glacier Inventory v7.0, Region 13 (Central Asia)
- **Format**: Shapefiles with glacier outlines (~2000 CE)
- **Processing**: Rasterized to 10m binary masks using `rasterio.features.rasterize`
- **Coverage**: 36,036 glaciers in RGI Region 13; subset to study area bbox

### 3.2.4 WGMS — Validation
- **Source**: WGMS Fluctuations of Glaciers database (FoG v2024-01)
- **Glacier**: Tuyuksu (WGMS ID: 11160)
- **Data Used**: Annual area measurements (1957–2023)
- **Purpose**: Independent validation of ML-derived area trends

---

## 3.3 Preprocessing Pipeline

### 3.3.1 Satellite Image Compositing
```
For each year Y in [2000..2024]:
  1. Filter scenes by date (July 1 – September 30)
  2. Remove cloudy pixels (QA60 + SCL)
  3. Compute per-pixel median across all cloud-free scenes
  4. Result: single 11-band composite image per year
```

### 3.3.2 Ground Truth Mask Creation
```
1. Load RGI shapefile for study area
2. Rasterize polygon to binary mask (0=background, 1=glacier)
3. Match extent and resolution to satellite composite
4. Apply buffer: 1-pixel erosion to reduce boundary noise
```

### 3.3.3 Patch Extraction
- **Patch Size**: 256×256 pixels
- **Stride**: 128 pixels (50% overlap for augmentation)
- **Class Balance**:
  - Keep patches with glacier fraction >1% (positive examples)
  - Randomly keep 30% of background patches (negative examples)
- **Augmentation** (training only):
  - Horizontal/vertical flips
  - 90° rotations (4 orientations)
  - Random brightness adjustment (±10%)
  - Random contrast adjustment (±10%)

### 3.3.4 Train/Val/Test Split
- 70% train / 15% validation / 15% test
- **Spatial separation**: patches from same glacier go to same split
- **Temporal separation**: if needed, test on held-out years

---

## 3.4 Model Architectures

### 3.4.1 U-Net (Baseline)
- **Encoder**: 4 downsampling blocks (Conv→BN→ReLU→Conv→BN→ReLU→MaxPool)
- **Decoder**: 4 upsampling blocks with skip connections
- **Filters**: [32, 64, 128, 256]
- **Parameters**: ~31M
- **Loss**: BCE + Dice (combined_loss)
- **Optimizer**: Adam (lr=1e-4)
- **Callbacks**: ReduceLROnPlateau (patience=8), EarlyStopping (patience=15)

### 3.4.2 Attention U-Net
- **Modification**: Attention gates on skip connections
- **Effect**: Suppresses irrelevant features, emphasizes glacier boundaries
- **Parameters**: ~34M (+10% vs U-Net)

### 3.4.3 U-Net++
- **Modification**: Dense nested skip connections (nested U-structured)
- **Depth**: 4 levels
- **Parameters**: ~40M (+29% vs U-Net)
- **Benefit**: Better feature fusion at multiple scales

### 3.4.4 NDSI Thresholding
- **Method**: Binary threshold on NDSI = (Green−SWIR)/(Green+SWIR)
- **Threshold**: Optimized on validation set (range 0.3–0.6)
- **Advantage**: No training required, fully interpretable
- **Limitation**: No spatial context, sensitive to illumination

### 3.4.5 Random Forest
- **Features**: 11-band pixel values + texture features (GLCM)
- **Trees**: 200, max_depth=15, class_weight='balanced'
- **Training**: Pixel-level classification (flatten patches)

### 3.4.6 Ensemble
- **Method**: Weighted averaging of probability maps
- **Weights**: 0.4×U-Net + 0.3×RF + 0.3×NDSI (tuned on validation)
- **Post-processing**: Optional CRF refinement (pydensecrf)

---

## 3.5 Evaluation Metrics

### 3.5.1 Segmentation Quality
- **Dice Coefficient**: 2×|A∩B|/(|A|+|B|) — primary metric
- **IoU (Jaccard)**: |A∩B|/(|A∪B|)
- **Precision**: TP/(TP+FP) — false positive rate
- **Recall**: TP/(TP+FN) — false negative rate
- **F1 Score**: Harmonic mean of Precision and Recall

### 3.5.2 Area Accuracy
- **RMSE**: √(Σ(A_pred−A_ref)²/N) against WGMS reference areas
- **Bias**: Mean(A_pred−A_ref) — systematic over/underestimation
- **R²**: Coefficient of determination

### 3.5.3 Uncertainty Quantification
- **MC-Dropout**: 10 forward passes with dropout enabled
- **Metric**: Standard deviation of pixel-wise predictions
- **Application**: Flag low-confidence pixels for manual review

---

## 3.6 Temporal Analysis

### 3.6.1 Glacier Area Time Series
```
For each year Y:
  1. Load composite image for year Y
  2. Run best model (ensemble or U-Net) → binary mask
  3. Count glacier pixels → area_km2 = pixels × (10m)² / 10⁶
  4. Store in results/tables/glacier_areas_all_years.csv
```

### 3.6.2 Trend Estimation
- **Method**: Ordinary Least Squares (OLS) linear regression
- **Model**: Area = β₀ + β₁×Year + ε
- **Metrics**: Slope (km²/year), p-value, R²
- **Forecast**: Extrapolate to 2050 with 95% confidence interval

### 3.6.3 WGMS Validation
- Compare ML-derived Tuyuksu area with WGMS annual measurements
- Compute RMSE, bias, and R²
- Target: RMSE <5% of mean glacier area

---

## 3.7 Reproducibility

### 3.7.1 Random Seeds
- All random operations use `np.random.default_rng(42)`
- TF/Python random seeds set at training start

### 3.7.2 Environment
- Python 3.10, TensorFlow 2.13, NumPy 1.24
- Conda for geospatial deps (gdal, rasterio, geopandas)
- pip for ML deps (tensorflow, scikit-learn)

### 3.7.3 Code Availability
- Full codebase: github.com/user/GlacierNET-KZ (public after competition)
- Notebooks: step-by-step reproduction of all results
- Docker: reproducible API deployment
