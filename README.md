# GlacierNET-KZ

[English](README.en.md) · [Documentation](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Ablation protocol](docs/ABLATION_PROTOCOL.md) · [Module maturity](docs/MODULE_MATURITY.md) · [API](docs/API_REFERENCE.md) · [Citation](CITATION.cff)

[![CI](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10–3.11](https://img.shields.io/badge/python-3.10–3.11-blue.svg)](https://www.python.org/downloads/)
[![FAIR](https://img.shields.io/badge/FAIR-Reproducible-green)](docs/REPRODUCIBILITY.md)
[![STAC 1.0](https://img.shields.io/badge/STAC-1.0-orange)](scripts/export_stac_catalog.py)

**GlacierNET-KZ** is an open-source Cryosphere Observation and Evidence OS for
planning what to observe next, coordinating field checks, and preserving an
auditable chain from data to human decision. Its scientific core remains an
open benchmark for glacier segmentation quality in Kazakhstan.

The project also ships
[CentralAsia-GlacierBench](benchmarks/centralasia_glacierbench/README.md), a
real-source, frozen-split evaluation suite for temporal segmentation,
cross-region transfer, external lake mapping, glacier motion, physical context,
and retrospective glacier-lake cascade screening. It never replaces missing
evidence with a synthetic score.

The project prioritises comparable acquisitions, leakage-resistant splits,
hard segmentation metrics, area error, temporal anomaly rejection, provenance,
and explicit limits on scientific claims. API, dashboard, Gradio and MCP tools
expose the verified artifacts; they are not substitutes for benchmark evidence.

## GlacierNET Operations

The [Operations MVP](docs/OPERATIONS_MVP.md) connects monitored assets,
observations, change candidates, Domain Shift Detector, Next Best Observation,
inspection tasks, signed field reports, evidence cases, human decisions, and a
SHA-256 audit chain.

It is deliberately a shadow-mode monitoring workspace—not an automatic warning
system. Open `http://localhost:8080/operations` after `./scripts/start.sh`. An
empty registry remains empty until a real local case or a typed field
observation is added.

## What It Does

- Builds glacier segmentation datasets from Sentinel-2, Landsat, and RGI data.
- Trains and compares the validated NDSI, Random Forest and U-Net core.
- Estimates annual glacier area with scene-QA and temporal-consistency gates.
- Produces confidence-aware reports with caveats, p-values, confidence intervals, and data-quality metadata.
- Exposes results through notebooks, REST API, dashboard, Gradio demo, and MCP-compatible tools.
- Exports reproducibility artifacts: STAC catalog, inventory tables, figures, metrics, and data citations.

## Current verified evidence

| Evaluation | Hard Dice | Hard IoU | Precision | Recall | Threshold | Scope |
|---|---:|---:|---:|---:|---:|---|
| 14-channel U-Net, 2024 year holdout | 0.8746 | 0.7771 | 0.9508 | 0.8097 | 0.2 | One AOI, RGI-derived silver labels |
| Compact S2 + terrain control, 2024 holdout | 0.8937 | 0.8078 | 0.9224 | 0.8668 | 0.3 | Same-patch ablation control |
| Compact control + Sentinel-1 VV/VH | **0.9036** | **0.8242** | 0.9252 | **0.8830** | 0.5 | Same patches, labels, splits, and training setup |

In the controlled experiment, Sentinel-1 increased hard Dice by **0.0099**,
hard IoU by **0.0164**, recall by **0.0163**, and reduced absolute area error
from 4.7873 to 3.6214 km². Precision increased by **0.0028**. Each model used
its own validation-calibrated threshold, frozen before test evaluation.

The evidence supports a one-AOI feature-ablation result only. It does not
establish cross-region generalisation, independent expert-label accuracy,
field accuracy, or operational readiness.

Historical area tables and forecasts under `results/` remain exploratory:
most annual prediction masks use deterministic NDSI, while RF/U-Net coverage
is not yet uniform across all years. See the
[validation protocol](docs/VALIDATION_PROTOCOL.md), the machine-validated
[benchmark report](results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json),
and the [controlled ablation report](results/ablation_sentinel1_2017_2024.json).

## Benchmark v2

The [benchmark v2 protocol](benchmarks/v2/protocol.md) freezes acquisition
rules, hard/boundary/area metrics, glacier-level bootstrap intervals, threshold
calibration and temporal rejection thresholds. The
[dataset card](benchmarks/v2/dataset_card.md) and
[annotation guidelines](benchmarks/v2/annotation_guidelines.md) define the
double-annotation gold workflow.

Current status is intentionally fail-closed:

- temporal one-AOI silver holdout: available;
- gold glacier-held-out benchmark: blocked until glacier-level annotations exist;
- Ile Alatau → Zhetysu Alatau external test: blocked until the external gold set exists.

Run the reproducible checks:

```bash
python scripts/assess_annual_scene_quality.py
python scripts/build_decision_readiness_tables.py
python scripts/validate_temporal_consistency.py
python scripts/validate_benchmark_v2.py --allow-incomplete  # structure
python scripts/validate_benchmark_v2.py                     # strict evidence gate
```

The strict command exits non-zero until both real-data blockers are resolved.
It is not bypassed with placeholder scores.

Automatic RGI pseudo-label cohorts now provide glacier-level paired confidence
intervals and an external-geography stress test. They are deliberately kept
outside the strict evidence gate; see [their limits and results](docs/PROVISIONAL_COHORTS.md).
The machine-readable [scientific claims registry](benchmarks/v2/claims_registry.json)
separates supported, refuted, provisional, and externally blocked statements.

The **Generalisation Sentinel** adds a frozen, physics-constrained
inventory-guided decoder for failure containment. Parameters selected on 18 Ile
Alatau glaciers were replayed without tuning on the nine-glacier provisional
external cohort. Mean hard Dice increased from 0.1815 to 0.5433 and mean
absolute area error fell from 1373.0% to 51.9%. This is a useful safeguard
result, not independent external accuracy: RGI is both the search prior and the
provisional comparison layer. The full paired intervals and circularity guard
are stored in
[`inventory_guided_decoder_2024.json`](benchmarks/v2/provisional/inventory_guided_decoder_2024.json).

## Active Cryosphere Risk Twin

The repository now includes a safety-bounded research baseline that turns
partial basin observations into an auditable latent state, screens glacier →
lake/slope → dam → channel → exposed-asset cascades, ranks the next observation
by model-based Value of Information, and abstains when evidence is missing,
uncertain or uncalibrated.

It deliberately does **not** output a GLOF probability or official warning.
The [Central Asia Cascade protocol](benchmarks/central_asia_cascade/protocol.md)
and [dataset card](benchmarks/central_asia_cascade/dataset_card.md) define the
retrospective evidence needed before those claims can be evaluated.

Run a JSON evidence payload locally:

```bash
python scripts/run_risk_twin.py evidence.json --output risk_twin_result.json
python scripts/validate_cascade_benchmark.py --allow-incomplete  # structure
python scripts/validate_cascade_benchmark.py                     # strict evidence gate
```

With the API running, inspect `GET /api/risk-twin/readiness` and submit evidence
to `POST /api/risk-twin/evaluate`. Output includes state uncertainty,
provenance, cascade coverage, abstention reasons, a next-observation ranking,
counterfactual screening and a Daily Decision Brief.

The resilience-aware extension adds virtual stress surfaces, observed recovery
diagnostics, model-defined resilience margins, Failure Genome hypotheses and
separate potential-hazard versus observation priorities. See the
[stress-test contract](docs/RESILIENCE_STRESS_TEST.md). An uncalibrated model
never produces a physical resilience claim.

### Source-backed Event Radar

`/event-radar` adds a live evidence queue above the Risk Twin. USGS and GDACS
work without credentials; optional official RSS/Atom feeds, ReliefWeb and
GDELT Cloud are enabled only when configured. Every signal keeps its source,
timestamp, coordinates, SHA-256 digest, distance to the selected RGI glacier
and a specific next observation. The system never turns media volume into a
GLOF probability (`hazard_probability` remains `null`).

See the [method and API contract](docs/OSINT_EVENT_RADAR.md) and the
[licence-aware open-source evaluation](docs/OSINT_OPEN_SOURCE_EVALUATION.md).

Use the Risk Twin interface to open a local RGI object or add a typed
observation. Missing local evidence produces an abstention and a collection
request; the product does not ship fabricated risk examples.

## Lake and GLOF evidence

The local evidence layer now includes three independently sourced datasets:

- NASA HMA_GLI 2015–2018: 22 lake polygons in the extended Ile Alatau AOI;
- Tien Shan inventories for 1990, 2000, 2010, 2020 and 2023: 103–317 AOI
  polygons per epoch after geometry repair;
- HMAGLOFDB v1.3.0: 58 geolocated historical events in the AOI.

Original Zenodo archives are retained with their published MD5 values and
locally computed SHA-256 hashes. Derived GeoPackages are EPSG:4326, spatially
clipped and have valid geometries. Machine-readable provenance and claim limits
live beside each artifact under `data/lakes/` and `data/events/`.

NASA CMR also reports candidate SWOT LakeSP and ICESat-2 ATL13 granules for the
AOI. These are metadata intersections, not yet confirmed lake observations, so
the project stores the lightweight query result rather than downloading about
77 GB of unfiltered granules.

Rebuild the derived layers and refresh the online coverage probe:

```bash
python scripts/build_lake_event_subsets.py
python scripts/probe_altimetry_coverage.py
```

These inventories and events support retrospective screening and benchmark
construction. They do not by themselves validate a present-day hazard,
forecast, GLOF probability or warning.

## Quick Start

### Option A: Unified Local Stack

Use this when you want the evidence workspace, API, and gateway under one localhost URL.

```bash
git clone https://github.com/nazkari86-lab/GlacierNET-KZ.git
cd GlacierNET-KZ
./scripts/start.sh
```

Open:

| Service | URL |
|---------|-----|
| Hub | http://localhost:8080/hub |
| ML evidence workspace | http://localhost:8080/ml |
| Risk Twin | http://localhost:8080/risk-twin |
| Operations | http://localhost:8080/operations |
| Local year explorer | http://localhost:8080/explore |
| Individual glacier registry | http://localhost:8080/glaciers |
| Segmentation UI | http://localhost:8080/predict |
| Guided workflow | http://localhost:8080/demo |
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

The older Gradio upload UI is optional and excluded from the default stack:

```bash
docker compose --profile legacy-demo up demo
# or for native development:
ENABLE_LEGACY_DEMO=1 ./scripts/start.sh --native
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

For the exact dependency-version set used by CI and the full Docker image, use
`pip install -r requirements.lock`.

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

### Verify the project without preparing imagery

Open `http://localhost:8080/explore`. The page reads the verified local
year-quality and decision-ready tables, then exposes only prediction files
that physically exist in `predictions/<year>/`. It supports one-year review
and caveated two-year comparison without uploading a file.

The `/predict` and `/demo` upload paths are expert workflows. They require a
calibrated multi-band Sentinel-2/Landsat GeoTIFF (or the bundled `.npy` demo
sample). Ordinary RGB photos do not contain the spectral bands required for
scientific segmentation.

Open `http://localhost:8080/glaciers` to search the 586-feature local RGI 7.0
study-area subset. A glacier card includes inventory geometry, elevation,
slope, length, physically computed per-year mask measurements, WGMS reference
points where available, an evidence-card export, and a preloaded AI context.
The time series is clipped to a fixed RGI 2000 outline and is explicitly
labelled as screening evidence rather than an independently delineated annual
boundary.

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
NDSI, Random Forest, U-Net
        |
        v
Hard/boundary/area metrics and calibrated threshold
        |
        v
Scene QA, temporal gate, holdout and bootstrap validation
        |
        v
FastAPI, Next.js dashboard, Gradio demo, STAC catalog, MCP tools
```

Additional model families remain experimental and are tracked separately in
[module maturity](docs/MODULE_MATURITY.md); they are not part of the validated
benchmark claim.

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
| `GROQ_API_KEY` | Optional server-side key for the Groq evidence assistant |

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
