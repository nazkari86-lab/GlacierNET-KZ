# Reproducibility Guide

> How to reproduce GlacierNET-KZ results on any machine — aligned with [FAIR](https://www.go-fair.org/fair-principles/) data principles and open-science best practices.

## Quick reproduction (no Earth Engine)

Verifies that the codebase is intact and the ML stack runs:

```bash
git clone https://github.com/nazkari86-lab/GlacierNET-KZ.git
cd GlacierNET-KZ
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev,api]"

python notebooks/_synthetic_smoke_test.py
python notebooks/_unet_smoke_test.py
pytest tests/ glacierkz-api/tests/ -q -m "not experimental"
```

Expected: all smoke tests pass; 380+ unit tests green in CI.

## Full scientific reproduction (2000–2020 results)

### 1. Environment lock

| Component | Version used in published results |
|-----------|-----------------------------------|
| Python | 3.10 |
| TensorFlow | ≥ 2.12 (tested with 2.13) |
| NumPy | 1.26.4 (after TF install) |
| rasterio | ≥ 1.3 |
| scikit-learn | ≥ 1.3 |

Use `requirements.txt` and record your exact versions:

```bash
pip freeze > reproduction/requirements-frozen.txt
```

### 2. Random seeds

All stochastic operations use fixed seeds defined in `src/config.py`:

- `RANDOM_SEED = 42` — train/val/test split, patch sampling
- TensorFlow/Keras: `tf.random.set_seed(42)` in training notebooks
- NumPy: `np.random.seed(42)` in preprocessing

### 3. Data acquisition

| Dataset | Source | License | Citation |
|---------|--------|---------|----------|
| Sentinel-2 L2A | Google Earth Engine | Copernicus (free) | See [DATA_CITATION.md](./DATA_CITATION.md) |
| Landsat 5/7/8 | Google Earth Engine | USGS (free) | See [DATA_CITATION.md](./DATA_CITATION.md) |
| RGI 7.0 region 13 | GLIMS/NSIDC | CC BY 4.0 | Pfeffer et al. (2014) |
| WGMS Tuyuksu | FoG 2026 | WGMS terms | See `data/wgms/tuyuksu_areas.json` |

Study area bounding box: **76.5–77.5°E, 42.8–43.2°N** (`STUDY_AREA_BBOX` in `src/config.py`).

Pipeline order:

```
notebooks/01_data_download.ipynb  → data/raw/
notebooks/02_preprocessing.ipynb  → data/processed/patches/
notebooks/03_baseline_models.ipynb
notebooks/04_unet_training.ipynb  → models/unet_best.h5
notebooks/05_temporal_analysis.ipynb → results/tables/
notebooks/06_visualization.ipynb  → results/figures/
```

### 4. Published metrics (reference)

From `results/tables/model_comparison.csv` and `paper/results_template.md`:

| Metric | Value |
|--------|-------|
| U-Net F1 / IoU | 0.876 / 0.780 |
| Area loss 2000–2020 | −129.5 km² (−22.4%) |
| Linear trend | −12.7 km²/yr (R² = 0.54) |
| Forecast 2050 | ~350 km² |

### 5. Docker (one-command stack)

```bash
./scripts/start.sh
# or: docker compose up --build
# Hub → http://localhost:8080/hub
```

Model weights must be present in `./models/` (not shipped in git — download from release assets or train locally).

### 6. STAC catalog export

For interoperability with QGIS, STAC Browser, and planetary-scale tools:

```bash
python scripts/export_stac_catalog.py --output results/stac/catalog.json
```

### 7. Validation scripts

```bash
python scripts/run_wgms_validation.py    # WGMS Tuyuksu cross-check
python scripts/evaluate_all_models.py    # Recompute F1/IoU on test set
python scripts/generate_figures.py       # Regenerate paper figures
```

### 8. Reporting issues

If your reproduction diverges, open a [GitHub Issue](https://github.com/nazkari86-lab/GlacierNET-KZ/issues) with:

1. `pip freeze` output
2. OS and Python version
3. Which notebook/step diverged
4. Expected vs actual metric

## FAIR checklist

| Principle | Implementation |
|-----------|----------------|
| **Findable** | GitHub repo, CITATION.cff, STAC catalog, HuggingFace demo |
| **Accessible** | MIT license, open API, Docker Compose |
| **Interoperable** | GeoTIFF I/O, STAC JSON, REST OpenAPI, MCP tools |
| **Reusable** | Documented config, frozen requirements, WGMS validation |
