# GlacierNET-KZ — Agent Context

## Project Structure
- `glacierkz-api/` — FastAPI 0.109.0, Python 3.10-slim, SQLite (WAL mode, `results.db`)
- `glacierkz-web/` — Next.js 16.2.9 (bleeding edge, check compat), TypeScript, Tailwind
- `src/` — All ML code (models, data loading, preprocessing, training, metrics)
- `notebooks/` — Jupyter notebooks for EDA and pipeline steps (some diverge from generators)
- `data/raw/` — Landsat (2000–2013), Sentinel-2 (2015–2024; 2015 late-year TOA fallback) rasters, RGI shapefiles
- `data/processed/patches/2020/` — Only year with preprocessed .npy patches for training
- `docs/` — literature_review.md (14 sources), contacts_and_partnerships.md (5 contacts), checklist.md (47 items, 34 done), `wgms_validation.md`
- `paper/` — draft_outline.md filled with real results from `results/tables/` and `predictions/`
- `scripts/` — `generate_figures.py`, `train_unet_plus_plus.py`, `wgms_setup.py`

## Stack
- **Backend**: FastAPI + TensorFlow 2.21 + NumPy 1.26 + Redis + liteLLM
- **Frontend**: Next.js 16.2.9 (App Router) + Leaflet + Recharts + shadcn/ui
- **ML**: U-Net, U-Net++, Attention U-Net, Random Forest, NDSI threshold, ensemble (5 models)
- **11 spectral channels**: 7 Sentinel-2 bands + 4 indices (NDSI, NDWI, BSI, EVI)
- **Inference**: Sliding window 256×256, 50% overlap, TTA (3 flips), MC-Dropout uncertainty
- **Training**: 70/15/15 split, batch=8, 100 epochs, Adam 1e-4, ReduceLROnPlateau+EarlyStopping+TensorBoard
- **LLM Gateway**: liteLLM (multi-provider router) + Ollama local fallback; `app/services/llm_service.py`
- **LLM Providers**: OpenAI, Anthropic, Groq (free), Google Gemini, Ollama (free/local), OpenRouter
- **CI/CD**: GitHub Actions (lint + test + typecheck + security + docker-build), ruff, pytest, pyright
- **Code quality**: ruff check + format clean, `.env.example` for all services

## Critical Conventions & Findings
- **SECURITY**: `download_drive.py` had hardcoded `client_secret` — now reads from `GOOGLE_CLIENT_SECRET` env var
- **Model cache**: `_MODEL_CACHE` / `_RF_MODEL` in `segmentation_service.py` use `threading.Lock` (`_cache_lock`) for concurrent requests
- **Max file size**: 200 MB, configurable via `MAX_FILE_SIZE_MB` env var
- **seed_db.py**: runs standalone via `__name__ == "__main__"` — requires `sys.path` hacks (acceptable for seed scripts)
- **Path resolution**: `segmentation_service.py` finds `src/` package via `CORE_DIR` env var (set in Dockerfile), falls back to relative path from `__file__`
- **Notebook divergence**: `01_data_download.ipynb` manually edited, diverges from `_generate_notebooks.py` generator
- **05_temporal_analysis.ipynb**: WGMS cell still expects `data/wgms/tuyuksu_areas.json` — use `scripts/wgms_setup.py` + `docs/wgms_validation.md`
- **CORS_ORIGINS**: now strips whitespace after split
- **Model weights**: `unet_best.h5`, `attention_unet_best.h5`, `unet_plus_plus_best.h5`, `random_forest.pkl` exist locally (gitignored)
- **Checklist**: raw data baseline complete — remaining: multi-year Sentinel patch dataset, EDA, RF feature importance, public release prep
- **Paper**: `paper/draft_outline.md` filled with metrics from `results/tables/model_comparison.csv`, temporal series from `glacier_areas_all_years.csv`

## Key Results (real data, 2000–2020)
| Metric | Value |
|--------|-------|
| U-Net F1 / IoU | 0.8763 / 0.7798 |
| Random Forest F1 | 0.8525 |
| NDSI F1 | 0.8513 |
| Area loss 2000–2020 | −129.53 km² (−22.4%) |
| Trend (linear RF) | −12.66 km²/yr, R²=0.54 |
| Forecast 2050 | ~350 km² (−38% from 2000) |
| Water supply equiv. | ~10 years (Almaty) |

## CI/CD & Quality
- **GitHub Actions**: `.github/workflows/ci.yml` — lint (ruff) + test (pytest) + typecheck (pyright) + frontend-test (vitest) + security (bandit/safety) + validate (env) + docker-build (api+web)
- **Lint**: `ruff check + format` — 60 remaining E402 only (sys.path hacks in tests, acceptable)
- **Tests**: root suite `411 passed`; API suite `419 passed, 2 skipped`; web unit suite `170 passed`
- **Install**: `pip install -r requirements.txt` or `pip install -e ".[dev,api]"` (deps declared in `pyproject.toml`)

## U-Net++ Weights

`models/unet_plus_plus_best.h5` is present locally. Retrain only when changing
the architecture, loss, or patch dataset.

**Prerequisites for retraining**: patches at `data/processed/patches/2020/`
(from `02_preprocessing.ipynb`).

```bash
# Option A — dedicated script
python scripts/train_unet_plus_plus.py --year 2020

# Option B — generic trainer
python -m src.train --model unet_plus_plus --year 2020 --no-attention

# Option C — notebook
# Run notebooks/04_unet_training.ipynb with config.MODEL_NAME = "unet_plus_plus"
```

Output: `models/unet_plus_plus_best.h5`, log in `results/training_log.csv`.
Do **not** run full training in CI — ~1–3 h locally with early stopping.

## WGMS Validation

1. Download FoG: https://doi.org/10.5904/wgms-fog-2026-02-10 (~868 MB)
2. `python scripts/wgms_setup.py --fog-csv /path/to/measurements.csv`
3. Load JSON in `05_temporal_analysis.ipynb` — see `docs/wgms_validation.md`

## Next Steps Recommended
1. Build a reproducible multi-year Sentinel-2 patch dataset beyond the existing 2020 patches
2. Keep `scripts/validate_data_quality.py`, `scripts/build_data_inventory.py`, and `scripts/export_stac_catalog.py` green after every data change
3. Recompute area/trend tables with explicit provenance columns and 95% CI/p-value fields
4. Run WGMS validation in notebook 05 after confirming FoG extraction
5. `seed_db.py` for full history in API database
6. Public release prep (walkthrough, release notes, external review)
