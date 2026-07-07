# ISEF Presentation — 7 Minutes

**GlacierNET-KZ: AI-Powered Glacier Monitoring in Kazakhstan**

Target: 7 min talk + 3 min Q&A · ~14 slides · ~30 sec per slide

---

## Slide 1 — Title (30 sec)

- Title, name, school, country
- One sentence: *"I built an AI system that maps glacier loss in Kazakhstan from satellite photos."*
- Show hero image: glacier panorama + segmentation overlay

---

## Slide 2 — The Problem (45 sec)

**Hook:** "Almaty drinks glacier water. Our glaciers are disappearing."

- 2.4 million people depend on meltwater
- −129.5 km² lost since 2000 (−22.4%)
- Climate change — but **nobody is monitoring automatically** in our region

*Speaker note:* Make it personal — local audience knows Big Almatinka river.

---

## Slide 3 — Why Existing Methods Fail (30 sec)

- Manual mapping: slow, expensive, once per decade
- NDSI snow index: confuses rock, shadow, debris-covered ice
- **Gap:** Almost zero deep-learning work for Tian Shan glaciers (cite Springer 2025)

---

## Slide 4 — My Approach (45 sec)

**Diagram:** Satellite → 11 channels → U-Net → glacier map

- Sentinel-2 + Landsat, 2000–2020
- U-Net: learns patterns humans can't threshold
- 11 inputs: 7 spectral bands + 4 indices (NDSI, NDWI, BSI, EVI)
- Validated on WGMS glacier Tuyuksu (observations since 1957)

---

## Slide 5 — Data & Methods (45 sec)

| | |
|---|---|
| Area | Zailiysky Alatau, Kazakhstan |
| Images | 9 years Landsat + 3 years Sentinel-2 |
| Ground truth | RGI 7.0 glacier outlines |
| Training | 256×256 patches, 70/15/15 split |

- Google Earth Engine for download
- ~500+ training patches from real imagery

---

## Slide 6 — Model Comparison (45 sec)

**Bar chart:** F1 scores

| Method | F1 |
|--------|-----|
| NDSI | 0.851 |
| Random Forest | 0.853 |
| **U-Net** | **0.876** |

- U-Net wins by +2.5 percentage points
- Attention U-Net and U-Net++ comparable
- Show side-by-side prediction image (RGB | mask | overlay)

---

## Slide 7 — Temporal Results (45 sec)

**Line chart:** Area vs Year + forecast to 2050

- Steady decline: −12.7 km² per year
- 2050 forecast: ~350 km² (−38% from 2000)
- Equivalent to **10 years** of Almaty water supply lost

*Emphasize:* This is not a simulation — real satellite data, real measurements.

---

## Slide 8 — WGMS Validation (30 sec)

- Tuyuksu = WGMS reference glacier since 1957
- 25 years of independent ground measurements
- Our pipeline cross-checked against WGMS FoG database
- Shows scientific rigor for judges

---

## Slide 9 — Live Demo (30 sec)

- Screen recording or live: upload GeoTIFF → get mask in seconds
- HuggingFace Spaces demo
- Mention FastAPI + Next.js dashboard (EN/RU/KK)

*Fallback:* Pre-recorded 15-sec video if WiFi unreliable.

---

## Slide 10 — Innovation & Impact (45 sec)

**What's new:**
1. First DL glacier monitor for Kazakhstan Ili Alatau
2. Open-source, reproducible, 338 automated tests
3. Multilingual dashboard for scientists and policymakers

**Impact:**
- Annual automated monitoring (vs decadal manual)
- Supports water resource planning for Almaty
- Replicable for other Central Asian countries

---

## Slide 11 — Limitations & Future (30 sec)

- Debris-covered ice still hard
- Need more Sentinel-2 years (2018–2024)
- Plan: expand to Junggar Alatau, ensemble models

Honest limitations score well with ISEF judges.

---

## Slide 12 — Conclusion (30 sec)

> "I built GlacierNET-KZ — an AI that watches our glaciers from space.
> It proves we lost 22% in 20 years, and helps us plan for a water-scarce future."

- GitHub + demo QR code
- Thank you + questions

---

## Q&A Preparation (top 10 judge questions)

| Question | Answer |
|----------|--------|
| Why U-Net and not Segment Anything (SAM)? | SAM is zero-shot but untrained on alpine debris; U-Net trained on local spectra performs better (F1 0.876 vs NDSI 0.851). SAM planned as baseline. |
| How do you know ground truth is correct? | RGI 7.0 outlines from GLIMS + WGMS independent validation on Tuyuksu. |
| What about cloud cover? | Summer composites (Jul–Sep) with ≤20% cloud from GEE median compositing. |
| Can this work globally? | Architecture is generic; needs retraining per region. Code is open-source. |
| What's the uncertainty? | MC-Dropout provides pixel uncertainty maps; confidence intervals on 2050 forecast. |
| Did you do this alone? | Yes, with teacher mentorship; 338 tests, full CI pipeline. |
| Environmental impact of AI training? | ~2h training on Mac/GPU; inference seconds per image; much less than manual mapping flights. |
| How is this different from NASA/USGS products? | Regional focus, higher resolution, local validation, open code for Kazakhstan scientists. |
| Statistical significance of trend? | R² = 0.54, p < 0.05 for linear regression over 9 time points. |
| Next competition steps? | GENIUS Olympiad — environmental science category. |

---

## Timing checklist

- [ ] Rehearse with timer — target 6:30 to leave buffer
- [ ] Practice demo offline fallback
- [ ] Prepare 1-page handout with QR codes
- [ ] Test projector resolution (1920×1080)
