# GENIUS Olympiad — Environmental Science Submission

> GlacierNET-KZ submission package for [GENIUS Olympiad](https://geniusolympiad.org/) (Environmental Science / Climate Change track).

## Project title

**GlacierNET-KZ: AI-Powered Monitoring of Glacier Retreat Threatening Central Asia's Water Security**

## Category

Environmental Science — Climate Change & Remote Sensing

## One-sentence summary

We built an open-source deep-learning platform that maps glacier loss in Kazakhstan's Ili Alatau from satellite imagery, quantifies a 22.4% area decline (2000–2020), and forecasts continued retreat to 2050 — validated against 67 years of WGMS measurements at Tuyuksu glacier.

## Problem statement (global relevance)

- **2.4 million people** in Almaty depend on glacier meltwater from the Ili Alatau.
- Central Asian glaciers lost **~25% area** since 1960 (IPCC AR6); Kazakhstan's Tian Shan is data-sparse in ML literature.
- Manual glacier mapping is slow and inconsistent; NDSI thresholds fail on debris-covered ice.

## Innovation

| Aspect | Our contribution | Prior art |
|--------|------------------|-----------|
| Geography | First DL glacier segmentation pipeline for **Kazakhstan Ili Alatau** | Global models (e.g. GlaViTU) don't cover this region |
| Methods | 11-channel U-Net + ensemble (RF, NDSI, Attention U-Net) | Mostly NDSI or manual digitization in Central Asia |
| Validation | WGMS reference glacier **Tuyuksu** (since 1957) | Few ML papers validate against in-situ records |
| Open science | Full stack: code, API, dashboard (EN/RU/KK), HuggingFace demo | Most research code is not deployable |

## Key results

| Finding | Value | Source |
|---------|-------|--------|
| U-Net segmentation accuracy | F1 = 0.876, IoU = 0.780 | `results/tables/model_comparison.csv` |
| Glacier area loss 2000–2020 | −129.5 km² (−22.4%) | `results/tables/glacier_areas_all_years.csv` |
| Retreat rate | −12.7 km²/yr (R² = 0.54) | `src/metrics.trend_analysis` |
| Forecast 2050 | ~350 km² remaining | `src/metrics.forecast_to_2050` |
| Water supply impact | ~10 years of Almaty supply equivalent | `src/metrics.ice_volume_loss_to_water_supply` |

## Methods (judge-friendly)

1. **Data:** Sentinel-2 & Landsat summer composites via Google Earth Engine; RGI 7.0 glacier outlines.
2. **Preprocessing:** 256×256 patches, 11 channels (7 spectral bands + NDSI, NDWI, BSI, EVI).
3. **Model:** U-Net encoder-decoder with skip connections; compared against NDSI and Random Forest.
4. **Inference:** Sliding window (50% overlap), test-time augmentation, MC-Dropout uncertainty.
5. **Analysis:** Linear trend → forecast 2050; WGMS cross-validation at Tuyuksu.

## Demonstration

- **Live demo:** https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2
- **Source code:** https://github.com/nicklaua/GlacierNET-KZ
- **Dashboard:** `docker compose up` → http://localhost:3000

## Poster layout (90 cm × 120 cm, landscape)

Reuse sections from [ISEF_POSTER.md](./ISEF_POSTER.md) with these GENIUS-specific additions:

1. **Global context panel** — IPCC Central Asia glacier trends + Almaty water dependency map
2. **Environmental impact panel** — meltwater equivalent, forecast chart to 2050
3. **Open science panel** — QR codes to GitHub, HuggingFace, CITATION.cff
4. **Validation panel** — WGMS Tuyuksu time series overlay

## Oral presentation (5 minutes)

| Time | Section |
|------|---------|
| 0:00–0:45 | Hook: Almaty water crisis + visible glacier shrinkage |
| 0:45–1:30 | Problem: no ML tools for Kazakhstan glaciers |
| 1:30–3:00 | Solution: pipeline demo (show HuggingFace upload → mask) |
| 3:00–4:00 | Results: −22.4%, forecast 2050, WGMS validation |
| 4:00–4:45 | Impact: open platform for Central Asian researchers |
| 4:45–5:00 | Q&A setup |

## Judging criteria alignment

| Criterion | Evidence |
|-----------|----------|
| Scientific rigor | WGMS validation, 5-model comparison, published metrics in `paper/` |
| Environmental impact | Water supply analysis for 2.4M people |
| Innovation | First open DL platform for Kazakhstan glaciers |
| Presentation | Trilingual dashboard, live demo, reproducible Docker stack |
| Feasibility | Deployed API + web + HuggingFace; 380+ automated tests |

## Required citations

See [docs/DATA_CITATION.md](../docs/DATA_CITATION.md) for BibTeX entries (Sentinel-2, Landsat, RGI, WGMS, this software).

## Checklist before submission

- [ ] Poster printed at required dimensions
- [ ] Laptop with offline demo backup (Docker or cached predictions)
- [ ] USB with `results/figures/` and `paper/results_template.md`
- [ ] CITATION.cff and LICENSE printed for judges
- [ ] 3 rehearsal runs timed to 5:00 ± 15 s
