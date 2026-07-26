# GlacierNET-KZ

[Русская версия](README.md) · [Documentation](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [API](docs/API_REFERENCE.md) · [Citation](CITATION.cff)

[![CI](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10–3.11](https://img.shields.io/badge/python-3.10–3.11-blue.svg)](https://www.python.org/downloads/)
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

## Current verified evidence

| Evaluation | Dice | IoU | Precision | Recall | Scope |
|---|---:|---:|---:|---:|---|
| 14-channel U-Net, 2024 year holdout | 0.7802 | 0.7382 | 0.9712 | 0.7547 | One AOI, RGI-derived silver labels |
| Compact S2 + terrain control, 2024 holdout | 0.6942 | 0.7938 | 0.9507 | 0.8279 | Same-patch ablation control |
| Compact control + Sentinel-1 VV/VH | 0.7092 | 0.8242 | 0.9252 | 0.8830 | Same patches, labels, splits, and training setup |

In the controlled experiment, Sentinel-1 increased Dice by **0.0150**, IoU by
**0.0304**, and recall by **0.0551**, while precision decreased by **0.0255**.
The evidence supports a one-AOI feature-ablation result only. It does not
establish cross-region generalisation, independent expert-label accuracy,
field accuracy, or operational readiness.

Historical area tables and forecasts under `results/` remain exploratory:
most annual prediction masks use deterministic NDSI, while RF/U-Net coverage
is not yet uniform across all years. See the
[validation protocol](docs/VALIDATION_PROTOCOL.md), the machine-validated
[benchmark report](results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json),
and the [controlled ablation report](results/ablation_sentinel1_2017_2024.json).

## Benchmark v2 and Active Cryosphere Risk Twin

Benchmark v2 freezes acquisition rules, hard and boundary metrics,
glacier-level bootstrap intervals, threshold calibration, and
leakage-resistant temporal/glacier/region splits. Its strict evidence gate
remains fail-closed until expert gold annotations and an external-region cohort
exist. See [the protocol](benchmarks/v2/protocol.md).

The tested Active Cryosphere Risk Twin research baseline assimilates partial
basin observations, screens glacier-to-asset cascades, ranks the next
observation by model-based Value of Information, and abstains when evidence is
missing or uncalibrated. It does not output an operational GLOF probability or
official warning. See the
[Central Asia Cascade protocol](benchmarks/central_asia_cascade/protocol.md)
and [module maturity inventory](docs/MODULE_MATURITY.md).

```bash
python scripts/validate_benchmark_v2.py --allow-incomplete
python scripts/validate_cascade_benchmark.py --allow-incomplete
python scripts/run_risk_twin.py evidence.json --output risk_twin_result.json
```

## Lake and GLOF evidence

The local evidence layer includes NASA HMA_GLI 2015–2018, five Tien Shan lake
inventory epochs from 1990–2023, and HMAGLOFDB v1.3.0 historical events.
Published checksums, local SHA-256 hashes, licences, processing details and
claim limits are stored in adjacent manifests under `data/lakes/` and
`data/events/`.

Compact AOI GeoPackages are published; third-party source archives remain
local. NASA CMR candidate metadata for SWOT LakeSP and ICESat-2 ATL13 is kept
under `data/online_coverage/`. Candidate intersections are not presented as
confirmed lake observations.

```bash
python scripts/build_lake_event_subsets.py
python scripts/probe_altimetry_coverage.py
```

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
