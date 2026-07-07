---
title: GlacierNET-KZ — AI Glacier Monitoring
emoji: 🏔️
colorFrom: blue
colorTo: white
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# GlacierNET-KZ

ML-based glacier monitoring for Kazakhstan's Ili Alatau using U-Net and satellite imagery.

## Features

- **Upload satellite image** → Get glacier classification mask
- **Interactive visualization** of predictions with confidence maps
- **Model comparison**: U-Net vs Random Forest vs NDSI
- **Time series**: Glacier area trends 2000–2020

## How to Use

1. Upload a Sentinel-2 or Landsat composite image (GeoTIFF)
2. Select the classification method
3. View the glacier mask, RGB overlay, and confidence map

## Model Performance

| Method | F1 | IoU |
|--------|-----|------|
| U-Net (Attention) | 0.876 | 0.780 |
| Random Forest | 0.853 | 0.743 |
| NDSI | 0.851 | 0.741 |

## Data

- Sentinel-2 (10m) for 2016–2020
- Landsat (30m) for 2000–2013
- RGI 7.0 glacier outlines for training

## Citation

```bibtex
@software{glaciernetkz2026,
  title={GlacierNET-KZ: ML Glacier Monitoring for Kazakhstan},
  author={Nick Laua},
  year={2026},
  url={https://github.com/nicklaua/GlacierNET-KZ}
}
```
