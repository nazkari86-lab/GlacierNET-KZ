# GlacierNET-KZ

**Deep-learning glacier monitoring for Kazakhstan** — Zailiysky & Junggar Alatau (Ili Alatau), using U-Net on Sentinel-2 / Landsat imagery.

Built for international science competitions: **Daryn → ISEF → GENIUS Olympiad**.

[![CI](https://github.com/nicklaua/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nicklaua/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FAIR](https://img.shields.io/badge/FAIR-Reproducible-green)](docs/REPRODUCIBILITY.md)
[![STAC 1.0](https://img.shields.io/badge/STAC-1.0.0-orange)](scripts/export_stac_catalog.py)
[![HuggingFace Spaces](https://img.shields.io/badge/🤗-Live_Demo-yellow)](https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2)

[Русская версия](README.md) · [Docs](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Data Citations](docs/DATA_CITATION.md) · [Architecture](docs/ARCHITECTURE.md)

---

## Highlights

| Metric | Value |
|--------|-------|
| U-Net F1 / IoU | **0.876 / 0.780** |
| Random Forest F1 | 0.853 |
| NDSI baseline F1 | 0.851 |
| Area loss 2000–2020 | **−129.5 km² (−22.4%)** |
| Linear trend | −12.7 km²/yr (R² = 0.54) |
| Forecast 2050 | ~350 km² (−38% vs 2000) |
| Almaty water-supply equivalent | ~10 years |

**Scientific gap:** Deep-learning glacier mapping for Tian Shan and Junggar Alatau is largely absent in the literature (see `docs/literature_review.md`).

---

## International standards

| Standard | Implementation |
|----------|----------------|
| **Open science** | MIT license, full source, trained weights via releases |
| **FAIR data** | [Reproducibility guide](docs/REPRODUCIBILITY.md), fixed seeds, Docker stack |
| **Geospatial interop** | GeoTIFF I/O, [STAC 1.0 catalog](scripts/export_stac_catalog.py), WGS84 bbox |
| **Data provenance** | [BibTeX citations](docs/DATA_CITATION.md) for Sentinel-2, Landsat, RGI, WGMS |
| **Accessibility** | Trilingual UI (EN / RU / KK), OpenAPI docs, HuggingFace demo |
| **Quality assurance** | 400+ tests, Ruff, Pyright, Playwright E2E, Bandit security scan |
| **Competition ready** | [ISEF poster](competition/ISEF_POSTER.md), [GENIUS package](competition/GENIUS_OLYMPIAD.md) |

---

## Live Demo

🏔️ **[HuggingFace Spaces](https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2)** — upload a GeoTIFF and get an ice mask in seconds.

### Unified local stack (one URL)

```bash
./scripts/start.sh
# or: docker compose up --build
```

| Service | URL |
|---------|-----|
| **Hub (start here)** | http://localhost:8080/hub |
| Dashboard | http://localhost:8080/dashboard |
| Gradio demo | http://localhost:8080/demo |
| API docs | http://localhost:8080/docs |
| MCP tools | http://localhost:8080/mcp/tools |
| Classic UI | http://localhost:8080/legacy |
| Health | http://localhost:8080/health |

Native dev (faster hot-reload): `./scripts/start.sh --native`

---

## Architecture

```
Satellite imagery (Sentinel-2 / Landsat)
        ↓
  Preprocessing (11 channels: 7 bands + NDSI, NDWI, BSI, EVI)
        ↓
  U-Net / U-Net++ / Attention U-Net / RF / NDSI ensemble
        ↓
  Sliding-window inference (256×256, 50% overlap, TTA, MC-Dropout)
        ↓
  Temporal analysis → trend → forecast to 2050
        ↓
  FastAPI + Next.js dashboard + HuggingFace Spaces + STAC catalog
```

**Languages:** Python (ML core), FastAPI (REST + WebSocket), Next.js 16 (EN/RU/KK i18n), Go/C/Java/.NET bindings.

---

## Quick Start

### 1. Environment

```bash
conda create -n glaciers python=3.10
conda activate glaciers
conda install -c conda-forge gdal rasterio geopandas shapely fiona
pip install -r requirements.txt
pip install -e ".[dev,api]"
```

### 2. Smoke tests (no Earth Engine required)

```bash
python notebooks/_synthetic_smoke_test.py
python notebooks/_unet_smoke_test.py
pytest tests/ -q
```

### 3. Full pipeline (local machine + GEE)

```bash
earthengine authenticate
# Run notebooks 01 → 06 in order
jupyter lab notebooks/
```

### 4. Export STAC catalog

```bash
python scripts/export_stac_catalog.py
# → results/stac/catalog.json
```

### 5. Train U-Net++

```bash
python scripts/train_unet_plus_plus.py --year 2020
```

---

## Project Structure

| Path | Description |
|------|-------------|
| `src/` | ML core: preprocessing, U-Net, metrics, visualization |
| `glacierkz-api/` | FastAPI backend (segmentation, trend, LLM analysis) |
| `glacierkz-web/` | Next.js dashboard (EN/RU/KK) |
| `notebooks/` | Pipeline notebooks 01–06 |
| `docs/` | Architecture, API, reproducibility, data citations |
| `competition/` | ISEF poster, GENIUS Olympiad package |
| `models/` | Trained weights (gitignored) |
| `results/` | Figures, CSV tables, STAC catalog |
| `paper/` | Scientific paper draft |

---

## Citation

If you use this project in research or competitions, please cite:

```bibtex
@software{glaciernet_kz_2026,
  author  = {Nurlanuly, Dulat},
  title   = {GlacierNET-KZ: Deep Learning Glacier Monitoring for Kazakhstan},
  year    = {2026},
  version = {0.2.0},
  url     = {https://github.com/nicklaua/GlacierNET-KZ},
  license = {MIT}
}
```

See also [`CITATION.cff`](CITATION.cff) and [`docs/DATA_CITATION.md`](docs/DATA_CITATION.md) for satellite and glacier inventory citations.

---

## Target Glaciers

Priority #1: **Tuyuksu** (WGMS reference glacier, measurements since 1957).  
See `src/config.py` → `GLACIERS`.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome contributions from glaciologists, ML engineers, and remote-sensing researchers worldwide.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 nazkari86-lab
