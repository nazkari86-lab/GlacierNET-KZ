# GlacierNET-KZ

[English](README.en.md) · [Documentation](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [API](docs/API_REFERENCE.md) · [Citation](CITATION.cff)

[![CI](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FAIR](https://img.shields.io/badge/FAIR-Reproducible-green)](docs/REPRODUCIBILITY.md)
[![STAC 1.0](https://img.shields.io/badge/STAC-1.0-orange)](scripts/export_stac_catalog.py)

**GlacierNET-KZ** is an open-source geospatial AI platform for monitoring glacier retreat in Kazakhstan. It combines Sentinel-2 and Landsat imagery, RGI/WGMS glacier references, spectral indices, Random Forest baselines, U-Net models, a FastAPI backend, a Next.js dashboard, STAC metadata, and reproducible notebooks.

The project is designed for researchers, climate analysts, GIS teams, educators, and public-sector users who need a transparent workflow from raw satellite imagery to glacier masks, area-change tables, trend analysis, and decision-ready reports.

## What It Does

- Builds glacier segmentation datasets from Sentinel-2, Landsat, and RGI data.
- Trains and compares NDSI, Random Forest, U-Net, Attention U-Net, and U-Net++ models.
- Estimates annual glacier area and long-term retreat trends.
- Produces confidence-aware reports with caveats, p-values, confidence intervals, and data-quality metadata.
- Exposes results through notebooks, REST API, dashboard, Gradio demo, and MCP-compatible tools.
- Exports reproducibility artifacts: STAC catalog, inventory tables, figures, metrics, and data citations.

## Current Results

| Metric | Value |
|--------|-------|
| U-Net F1 / IoU | 0.876 / 0.780 |
| Random Forest F1 | 0.853 |
| NDSI baseline F1 | 0.851 |
| Glacier area loss, 2000-2020 | -129.5 km² (-22.4%) |
| Linear trend | -12.7 km²/year |
| Forecast to 2050 | ~350 km² |
| Main reference glacier | Tuyuksu, Kazakhstan |

Results are stored under `results/`, with methodology notes in `paper/` and reproducibility instructions in `docs/REPRODUCIBILITY.md`.

## Quick Start

### Option A: Unified Local Stack

Use this when you want the dashboard, API, demo, and gateway under one localhost URL.

```bash
git clone https://github.com/nazkari86-lab/GlacierNET-KZ.git
cd GlacierNET-KZ
./scripts/start.sh
```

Open:

| Service | URL |
|---------|-----|
| Hub | http://localhost:8080/hub |
| Dashboard | http://localhost:8080/dashboard |
| Segmentation UI | http://localhost:8080/predict |
| Gradio demo | http://localhost:8080/demo |
| API docs | http://localhost:8080/docs |
| MCP tools | http://localhost:8080/mcp/tools |
| Health check | http://localhost:8080/health |

For hot-reload development:

```bash
./scripts/start.sh --native
```

To stop native services:

```bash
./scripts/start.sh --stop
```

### Option B: Python Pipeline Only

Use this when you want to run notebooks, tests, model training, or data processing locally.

```bash
conda create -n glaciers python=3.10
conda activate glaciers
conda install -c conda-forge gdal rasterio geopandas shapely fiona
pip install -r requirements.txt
pip install -e ".[dev,api]"
```

Run smoke checks that do not require Earth Engine:

```bash
python notebooks/_synthetic_smoke_test.py
python notebooks/_unet_smoke_test.py
pytest tests/ -q
```

### Option C: Frontend Only

```bash
cd glacierkz-web
npm install
npm run dev
```

The frontend reads API configuration from `NEXT_PUBLIC_API_URL`. For the unified gateway, leave it empty so browser requests stay same-origin.

## Full Data Pipeline

The full workflow requires a local machine with internet access, Google Earth Engine authentication, and enough disk space for raster data.

### 1. Authenticate Earth Engine

```bash
earthengine authenticate
```

### 2. Download Inputs

Run:

```bash
jupyter lab notebooks/
```

Execute notebooks in order:

| Step | Notebook | Output |
|------|----------|--------|
| 01 | `01_data_download.ipynb` | Sentinel-2, Landsat, RGI inputs |
| 02 | `02_preprocessing.ipynb` | masks, patches, train/val/test arrays |
| 03 | `03_baseline_models.ipynb` | NDSI and Random Forest metrics |
| 04 | `04_unet_training.ipynb` | U-Net weights and training logs |
| 05 | `05_temporal_analysis.ipynb` | area tables, trends, forecast |
| 06 | `06_visualization.ipynb` | final maps and figures |

Expected local data layout:

```text
data/
  raw/
    sentinel2/
    landsat/
  rgi/
  processed/
    masks/
    patches/
```

### 3. Validate Data Artifacts

```bash
python scripts/validate_data_quality.py
python scripts/build_data_inventory.py
python scripts/export_stac_catalog.py
```

The STAC catalog is written to:

```text
results/stac/catalog.json
```

### 4. Train U-Net++

```bash
python scripts/train_unet_plus_plus.py --year 2020
```

Model weights are stored in `models/`. Large model and raster artifacts are intentionally gitignored; publish them through releases or external storage.

## Architecture

```text
Sentinel-2 / Landsat / RGI / WGMS
        |
        v
Preprocessing and spectral indices
        |
        v
NDSI, Random Forest, U-Net, Attention U-Net, U-Net++
        |
        v
Sliding-window inference, TTA, uncertainty estimates
        |
        v
Temporal analysis, trend, forecast, validation
        |
        v
FastAPI, Next.js dashboard, Gradio demo, STAC catalog, MCP tools
```

## Repository Layout

| Path | Purpose |
|------|---------|
| `src/` | Core ML, preprocessing, metrics, visualization |
| `notebooks/` | Reproducible data and model pipeline |
| `glacierkz-api/` | FastAPI backend, REST, WebSocket, MCP bridge |
| `glacierkz-web/` | Next.js dashboard with EN/RU/KK localization |
| `glacierkz-mcp/` | Standalone MCP server |
| `spaces/` | HuggingFace Spaces / Gradio demo |
| `scripts/` | Training, validation, STAC, data-quality utilities |
| `docs/` | User, developer, API, architecture, and reproducibility docs |
| `results/` | Generated figures, tables, reports, and STAC catalog |
| `paper/` | Methodology and research write-up |
| `tests/` | Unit and integration tests |

## Environment Variables

Most users can start with `.env.example`.

Common variables:

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Frontend API base URL; empty for unified localhost |
| `NEXT_PUBLIC_SITE_URL` | Public site URL for metadata |
| `MAX_FILE_SIZE_MB` | API upload limit |
| `CORE_DIR` | Optional path to the core `src/` package |
| `GOOGLE_CLIENT_SECRET` | Google Drive/Earth Engine support scripts |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` | Optional LLM report providers |
| `OLLAMA_BASE_URL` | Optional local LLM fallback |

## Quality Checks

```bash
ruff check .
ruff format --check .
pytest tests/ -q
pyright
```

Frontend:

```bash
cd glacierkz-web
npm install
npm run lint
npm run test
npm run build
```

## Data and Citation

GlacierNET-KZ uses open satellite and glacier inventory sources. Cite the original providers when publishing derived results:

- Sentinel-2 / Copernicus
- Landsat / USGS
- RGI / GLIMS
- WGMS Fluctuations of Glaciers

See `docs/DATA_CITATION.md` and `CITATION.cff`.

## License

MIT. See `LICENSE`.
