# GlacierNET-KZ

[Русская версия](README.md) · [Documentation](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [API](docs/API_REFERENCE.md) · [Citation](CITATION.cff)

[![CI](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FAIR](https://img.shields.io/badge/FAIR-Reproducible-green)](docs/REPRODUCIBILITY.md)
[![STAC 1.0](https://img.shields.io/badge/STAC-1.0-orange)](scripts/export_stac_catalog.py)

**GlacierNET-KZ** is an open-source geospatial AI platform for monitoring glacier retreat in Kazakhstan. It combines Sentinel-2 and Landsat imagery, RGI/WGMS glacier references, spectral indices, Random Forest baselines, U-Net models, a FastAPI backend, a Next.js dashboard, STAC metadata, and reproducible notebooks.

## Quick Start

```bash
git clone https://github.com/nazkari86-lab/GlacierNET-KZ.git
cd GlacierNET-KZ
./scripts/start.sh
```

Open `http://localhost:8080/hub`.

For Python-only work:

```bash
conda create -n glaciers python=3.10
conda activate glaciers
conda install -c conda-forge gdal rasterio geopandas shapely fiona
pip install -r requirements.txt
pip install -e ".[dev,api]"
python notebooks/_synthetic_smoke_test.py
pytest tests/ -q
```

## Services

| Service | URL |
|---------|-----|
| Hub | http://localhost:8080/hub |
| Dashboard | http://localhost:8080/dashboard |
| Segmentation UI | http://localhost:8080/predict |
| Gradio demo | http://localhost:8080/demo |
| API docs | http://localhost:8080/docs |
| MCP tools | http://localhost:8080/mcp/tools |
| Health check | http://localhost:8080/health |

## Current Results

| Metric | Value |
|--------|-------|
| U-Net F1 / IoU | 0.876 / 0.780 |
| Random Forest F1 | 0.853 |
| NDSI baseline F1 | 0.851 |
| Glacier area loss, 2000-2020 | -129.5 km² (-22.4%) |
| Linear trend | -12.7 km²/year |
| Forecast to 2050 | ~350 km² |

## Full Workflow

1. Authenticate Google Earth Engine:

```bash
earthengine authenticate
```

2. Run notebooks in order:

| Step | Notebook | Output |
|------|----------|--------|
| 01 | `01_data_download.ipynb` | Sentinel-2, Landsat, RGI inputs |
| 02 | `02_preprocessing.ipynb` | masks, patches, train/val/test arrays |
| 03 | `03_baseline_models.ipynb` | NDSI and Random Forest metrics |
| 04 | `04_unet_training.ipynb` | U-Net weights and training logs |
| 05 | `05_temporal_analysis.ipynb` | area tables, trends, forecast |
| 06 | `06_visualization.ipynb` | final maps and figures |

3. Validate generated artifacts:

```bash
python scripts/validate_data_quality.py
python scripts/build_data_inventory.py
python scripts/export_stac_catalog.py
```

4. Train U-Net++ if needed:

```bash
python scripts/train_unet_plus_plus.py --year 2020
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

## Documentation

- `docs/BEGINNER_GUIDE.md` - plain-language project tour.
- `docs/ARCHITECTURE.md` - system architecture.
- `docs/API_REFERENCE.md` - REST, WebSocket, and MCP endpoints.
- `docs/REPRODUCIBILITY.md` - full reproduction procedure.
- `docs/DATA_CITATION.md` - data-source citations.
- `docs/UNIFIED_STACK.md` - single localhost gateway.

## Citation

```bibtex
@software{glaciernet_kz_2026,
  author  = {Nurlanuly, Dulat},
  title   = {GlacierNET-KZ: Geospatial AI Glacier Monitoring for Kazakhstan},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/nazkari86-lab/GlacierNET-KZ},
  license = {MIT}
}
```

See `CITATION.cff` and `docs/DATA_CITATION.md`.

## License

MIT. See `LICENSE`.
