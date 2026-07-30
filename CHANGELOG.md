# Changelog

All notable changes to GlacierNET-KZ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes.

## [0.4.0] - 2026-07-31

### Added

- Generalisation Sentinel: a frozen, physics-constrained inventory-guided
  decoder that suppresses disconnected seasonal-snow overmapping.
- Reproducible 18-glacier calibration and untouched nine-glacier provisional
  external replay with paired bootstrap intervals and explicit circularity
  guards.
- Per-glacier safeguarded GeoTIFF, geometry and diagnostics in the real ML
  evidence workflow and map.
- CentralAsia-GlacierBench with five model-evaluation tracks, four separately
  labelled reference-evidence tracks, publisher/source integrity records and
  no composite score.
- Strongest local Sentinel-1 + Sentinel-2 multimodal ablation as its own
  measured one-AOI silver-label track (Dice 0.9036, IoU 0.8242).
- Real HydroRIVERS `NEXT_DOWN` route tracing, a clearly labelled planning
  corridor and OSM objects selected for verification inside that corridor.
- Active Evidence Acquisition readiness gate that counts only source-reviewed
  events, verified controls, immutable pre-event snapshots and realised
  decision-loss reductions.

### Changed

- Scientific Evidence Cockpit and ML Workspace now expose the measured
  safeguard delta while continuing to block independent external-accuracy
  claims.
- Model evaluation is separated from physical and event reference evidence in
  the API and benchmark interface.
- Tests that rebuild decision-readiness tables now write to temporary paths and
  no longer mutate release artifacts.
- Product versions are aligned at `0.4.0`; the hub now foregrounds one
  four-step workflow: ML, Risk Twin, Operations and Benchmark.

## [0.2.0] - 2026-06-28

### Added
- **Unified gateway** on `http://localhost:8080` — Caddy reverse proxy for web, API, Gradio demo, MCP
- `./scripts/start.sh` — one-command Docker or native dev stack
- `/hub` service directory page (EN/RU/KK) in Next.js dashboard
- International documentation: [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) (FAIR principles), [DATA_CITATION.md](docs/DATA_CITATION.md) (BibTeX for all datasets)
- Research documentation and reproducibility package
- STAC 1.0.0 catalog export (`scripts/export_stac_catalog.py`) for QGIS / planetary-scale interoperability
- Documentation index ([docs/README.md](docs/README.md))
- GitHub Dependabot and release workflow for sustainable open-source maintenance
- English glacier names in `src/config.py` (`name_en` field)

### Changed
- Unified repository URLs to `nazkari86-lab/GlacierNET-KZ` across package metadata
- Enhanced README.en.md with international standards section and global positioning
- JsonLd structured data: citation, geographic coverage, free access flags

## [0.1.0] - 2026-06-27

### Added
- Full ML pipeline: preprocessing, U-Net / U-Net++ / Attention U-Net, NDSI and Random Forest baselines
- FastAPI backend with REST, WebSocket, MCP bridge, and LLM analysis gateway
- Next.js 16 dashboard with EN / RU / KK internationalization (345 translation keys)
- HuggingFace Spaces Gradio demo for real-time glacier segmentation
- Temporal trend analysis and forecast to 2050 with WGMS validation support
- GitHub Actions CI: Ruff, pytest (338 tests), Pyright, Vitest, Playwright E2E, Bandit, Docker build
- Docker Compose stack with Redis, API, and Web services with health checks
- SEO: `robots.txt`, `sitemap.xml`, JSON-LD structured data
- Scientific documentation: literature review, architecture, API reference, CITATION.cff

### Historical development results (real data, 2000–2020)

These v0.1 figures were internal development outputs, not independent
gold-label validation or an operational forecast. Current release gates do not
unlock those stronger claims.

- U-Net F1 / IoU: 0.876 / 0.780
- Glacier area loss: −129.5 km² (−22.4%)
- Linear trend: −12.7 km²/yr (R² = 0.54)
- Forecast 2050: ~350 km² (−38% vs 2000)

[0.2.0]: https://github.com/nazkari86-lab/GlacierNET-KZ/releases/tag/v0.2.0
[0.1.0]: https://github.com/nazkari86-lab/GlacierNET-KZ/releases/tag/v0.1.0
[0.4.0]: https://github.com/nazkari86-lab/GlacierNET-KZ/releases/tag/v0.4.0
