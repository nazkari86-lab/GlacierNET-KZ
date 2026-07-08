# Notebooks — Execution Guide

## Overview

Jupyter notebooks for the GlacierNET-KZ glacier monitoring pipeline.
Execute in order (01→06). Each notebook builds on outputs from the previous one.

## Prerequisites

```bash
# 1. Create conda environment for geospatial libs
conda create -n glaciers python=3.10
conda activate glaciers
conda install -c conda-forge gdal rasterio geopandas shapely fiona

# 2. Install ML and scientific libs
pip install -r requirements.txt

# 3. Start Jupyter
jupyter lab
```

## Notebook Execution Order

### 01_data_download.ipynb
- **Purpose**: Download Sentinel-2 and Landsat imagery from Google Earth Engine
- **Prerequisites**: GEE authentication (`earthengine authenticate`)
- **Inputs**: Study area bbox from `src/config.py`
- **Outputs**: `data/raw/sentinel2/`, `data/raw/landsat/`
- **Duration**: ~30 min (depends on GEE queue)
- **Notes**: Requires Google Earth Engine account. Skip if data already downloaded.

### 02_preprocessing.ipynb
- **Purpose**: Create training patches from satellite imagery + RGI masks
- **Inputs**: `data/raw/`, `data/rgi/`
- **Outputs**: `data/processed/patches/{year}/`
- **Duration**: ~15 min per year
- **Notes**: Uses `src/preprocessing.py:create_patches`. Only year 2020 has processed patches currently.

### 03_baseline_models.ipynb
- **Purpose**: Train and evaluate baseline models (NDSI, Random Forest, U-Net)
- **Inputs**: `data/processed/patches/2020/`
- **Outputs**: `models/`, `results/tables/model_comparison.csv`, `results/figures/`
- **Duration**: ~2 hours (U-Net training on GPU)
- **Notes**: Updates `BEST_NDSI_THRESHOLD` in config based on validation F1.

### 04_unet_training.ipynb
- **Purpose**: Detailed U-Net training with hyperparameter tuning
- **Inputs**: `data/processed/patches/`
- **Outputs**: `models/{unet,attention_unet,unet_plus_plus}_best.h5`
- **Duration**: ~3 hours (3 architectures × 100 epochs)
- **Notes**: Saves TensorBoard logs to `results/tensorboard/`.

### 05_temporal_analysis.ipynb
- **Purpose**: Apply trained models to all years, compute area time series, trend analysis
- **Inputs**: `data/raw/`, `models/`, WGMS data
- **Outputs**: `results/tables/glacier_areas_all_years.csv`, `results/tables/trend_statistics.csv`
- **Duration**: ~1 hour (inference across all years)
- **Notes**: Produces WGMS validation table. Fills placeholders in `paper/results_template.md`.

### 06_visualization.ipynb
- **Purpose**: Generate publication-quality figures
- **Inputs**: `results/tables/`, `results/figures/`
- **Outputs**: `results/figures/publication/`
- **Duration**: ~10 min
- **Notes**: Produces figures for the research write-up and dashboard.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'src'` | Run from project root or add `sys.path.insert(0, '.')` |
| `FileNotFoundError: RGI shapefile` | Download RGI 7.0 from https://nsidc.org/data/g02697 |
| OOM during U-Net training | Reduce `BATCH_SIZE` in `src/config.py` (default=8) |
| GEE authentication error | Run `earthengine authenticate` in terminal |
| GDAL import error | Use conda, not pip: `conda install -c conda-forge gdal` |

## Key Configuration

All notebook parameters are centralized in `src/config.py`:
- `STUDY_AREA_BBOX`: Geographic extent
- `YEARS_SENTINEL2` / `YEARS_LANDSAT`: Years to process
- `PATCH_SIZE`, `PATCH_STRIDE`: Patch extraction settings
- `BATCH_SIZE`, `EPOCHS`, `LEARNING_RATE`: Training hyperparameters
- `MODEL_NAME`: Architecture selection (unet/attention_unet/unet_plus_plus)
