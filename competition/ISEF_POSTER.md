# ISEF Poster — GlacierNET-KZ

**Board layout:** 122 cm × 91 cm (48" × 36") · Portrait · Sections left-to-right, top-to-bottom.

---

## Title Banner (full width)

**GlacierNET-KZ: Deep Learning Monitoring of Glacier Retreat in Kazakhstan's Ili Alatau**

Dulat Nurlanuly · [School Name] · Almaty, Kazakhstan

---

## 1. Introduction & Problem (top-left, ~25%)

### Why glaciers matter
- **22.4% area loss** in Zailiysky Alatau (2000–2020): −129.5 km²
- Almaty (2.4 M people) depends on glacier meltwater — **~10 years** of supply equivalent lost
- Climate change accelerates retreat across Central Asia

### Scientific gap
- Deep-learning glacier mapping for **Tian Shan / Junggar Alatau** is largely absent in literature (Springer 2025 review)
- Existing methods: manual outline digitization, NDSI threshold — low accuracy on debris-covered ice

**Figure:** `results/figures/glacier_maps_by_year.png` (multi-year map strip)

---

## 2. Hypothesis & Objectives (top-center)

**Hypothesis:** A U-Net trained on 11-channel Sentinel-2/Landsat composites (7 bands + NDSI, NDWI, BSI, EVI) outperforms classical NDSI and Random Forest baselines for glacier segmentation in Kazakhstan.

**Objectives:**
1. Build automated segmentation pipeline (GEE → patches → U-Net)
2. Compare 5 methods: NDSI, RF, U-Net, Attention U-Net, U-Net++
3. Quantify multi-decadal trend (2000–2020) and forecast to 2050
4. Validate against WGMS reference glacier **Tuyuksu** (ID 817, since 1957)

---

## 3. Methods (top-right, ~30%)

```
Sentinel-2 / Landsat → GEE composite (Jul–Sep)
        ↓
11 channels + RGI 7.0 masks → 256×256 patches
        ↓
U-Net (encoder-decoder, skip connections)
        ↓
Sliding-window inference (50% overlap, TTA, MC-Dropout)
        ↓
Area (km²) → linear trend → forecast 2050
```

| Parameter | Value |
|-----------|-------|
| Study area | 76.5–77.5°E, 42.8–43.2°N |
| Patch size | 256 × 256 px |
| Train/val/test | 70 / 15 / 15 % |
| Optimizer | Adam, lr=1e-4, early stopping |
| Channels | 7 S2 bands + 4 indices |

**Figure:** U-Net architecture diagram (from `paper/methodology.md`)
**Figure:** `results/figures/unet_test_samples.png`

---

## 4. Results (center, largest section ~40%)

### Model comparison (2020 test set)

| Method | F1 | IoU |
|--------|-----|-----|
| NDSI (threshold) | 0.851 | 0.741 |
| Random Forest | 0.853 | 0.743 |
| **U-Net** | **0.876** | **0.780** |
| Attention U-Net | 0.876 | 0.779 |
| U-Net++ | *see updated table* | |

### Temporal analysis

| Metric | Value |
|--------|-------|
| Area 2000 | 579 km² (RF) |
| Area 2020 | ~450 km² |
| Loss rate | **−12.7 km²/yr** (R² = 0.54) |
| Forecast 2050 | **~350 km²** (−38% vs 2000) |

**Figure:** `results/figures/glacier_trend_forecast.png`
**Figure:** `results/figures/model_comparison_f1.png`

### WGMS validation (Tuyuksu)
- 25 years of independent ground-truth (1958–2025) from WGMS FoG
- Reference glacier since 1957 — longest record in Central Asia

---

## 5. Discussion & Conclusions (bottom-left)

### Key findings
1. U-Net improves F1 by **+2.5 pp** over best baseline (RF)
2. Glacier retreat is **accelerating** — linear model may underestimate future loss
3. Automated pipeline enables **annual monitoring** without manual digitization

### Limitations
- Debris-covered ice remains challenging
- Single-region training — transfer to Junggar Alatau needs validation
- WGMS RMSE requires glacier-level crop (not full bbox)

### Future work
- U-Net++ ensemble, SAM zero-shot baseline
- Expand to Sentinel-2 2015–2024 full series
- Deploy via HuggingFace Spaces + FastAPI dashboard

---

## 6. References & QR Codes (bottom-right)

1. WGMS FoG 2026 — doi:10.5904/wgms-fog-2026-02-10
2. RGI 7.0 — GLIMS Consortium
3. Ronneberger et al. 2015 — U-Net
4. Springer 2025 — DL review for Kazakhstan glaciers
5. *See `docs/literature_review.md` (14 sources)*

**QR codes:**
- 🤗 Live Demo: https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2
- GitHub: https://github.com/nicklaua/GlacierNET-KZ
- API Docs: `/docs` (when deployed)

---

## Design notes for Canva / PowerPoint / LaTeX beamerposter

- **Color palette:** Ice blue `#3b82f6`, glacier white `#f8fafc`, alert red `#ef4444` for loss trend
- **Font:** Sans-serif (Geist / Inter), min 24 pt body, 48 pt titles
- **Photos:** Zailiysky Alatau panorama (credit source), Tuyuksu glacier (WGMS)
- **Print:** 300 DPI, CMYK if printing professionally
