# Changelog

All notable changes to GlacierNET-KZ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-28

### Added
- **Unified gateway** on `http://localhost:8080` — Caddy reverse proxy for web, API, Gradio demo, MCP
- `./scripts/start.sh` — one-command Docker or native dev stack
- `/hub` service directory page (EN/RU/KK) in Next.js dashboard
- International documentation: [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) (FAIR principles), [DATA_CITATION.md](docs/DATA_CITATION.md) (BibTeX for all datasets)
- [GENIUS Olympiad](competition/GENIUS_OLYMPIAD.md) submission package
- STAC 1.0.0 catalog export (`scripts/export_stac_catalog.py`) for QGIS / planetary-scale interoperability
- Documentation index ([docs/README.md](docs/README.md))
- GitHub Dependabot and release workflow for sustainable open-source maintenance
- English glacier names in `src/config.py` (`name_en` field)

### Changed
- Unified repository URLs to `nicklaua/GlacierNET-KZ` across package metadata
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

### Results (real data, 2000–2020)
- U-Net F1 / IoU: 0.876 / 0.780
- Glacier area loss: −129.5 km² (−22.4%)
- Linear trend: −12.7 km²/yr (R² = 0.54)
- Forecast 2050: ~350 km² (−38% vs 2000)

[0.2.0]: https://github.com/nicklaua/GlacierNET-KZ/releases/tag/v0.2.0
[0.1.0]: https://github.com/nicklaua/GlacierNET-KZ/releases/tag/v0.1.0
