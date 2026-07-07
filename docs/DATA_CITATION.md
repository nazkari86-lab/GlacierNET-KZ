# Data Citation Guide

> Required citations when using GlacierNET-KZ in ISEF, GENIUS Olympiad, journal papers, or posters. Follow each data provider's terms of use.

## Satellite imagery

### Sentinel-2 (Copernicus)

```bibtex
@misc{copernicus_s2_2024,
  author = {{European Space Agency}},
  title  = {Sentinel-2 MSI Level-2A},
  year   = {2024},
  note   = {Accessed via Google Earth Engine},
  url    = {https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED}
}
```

In-text: *Sentinel-2 Level-2A surface reflectance (Copernicus/ESA, via Google Earth Engine).*

### Landsat (USGS)

```bibtex
@misc{usgs_landsat_2024,
  author = {{U.S. Geological Survey}},
  title  = {Landsat Collection 2 Level-2},
  year   = {2024},
  note   = {Accessed via Google Earth Engine},
  url    = {https://developers.google.com/earth-engine/datasets/catalog/LANDSAT}
}
```

In-text: *Landsat 5/7/8 Collection 2 Level-2 (USGS, via Google Earth Engine).*

## Glacier inventories

### Randolph Glacier Inventory 7.0

```bibtex
@article{pfeffer2014rgi,
  author  = {Pfeffer, W. Tad and others},
  title   = {The {R}andolph {G}lacier {I}nventory: a globally complete inventory of glaciers},
  journal = {Journal of Glaciology},
  volume  = {60},
  number  = {221},
  pages   = {537--552},
  year    = {2014},
  doi     = {10.3189/2014JoG13J176}
}
```

Region used: **RGI 7.0 region 13 — Central Asia**.

### GLIMS

```bibtex
@misc{glims2024,
  author = {{Global Land Ice Measurements from Space}},
  title  = {GLIMS Glacier Database},
  year   = {2024},
  url    = {https://www.glims.org/}
}
```

## In-situ validation

### WGMS — Tuyuksu (ID 817)

```bibtex
@misc{wgms2026,
  author = {{World Glacier Monitoring Service}},
  title  = {Fluctuations of Glaciers Database},
  year   = {2026},
  url    = {https://wgms.ch/},
  note   = {Reference glacier Tuyuksu (Kazakhstan), measurements since 1957}
}
```

Local copy: `data/wgms/tuyuksu_areas.json` (25 years, FoG 2026 extract).

## Software

### This repository

```bibtex
@software{glaciernet_kz_2026,
  author  = {Nurlanuly, Dulat},
  title   = {GlacierNET-KZ: Deep Learning Glacier Monitoring for Kazakhstan},
  year    = {2026},
  url     = {https://github.com/nicklaua/GlacierNET-KZ},
  version = {0.2.0},
  license = {MIT}
}
```

Or use [`CITATION.cff`](../CITATION.cff) for GitHub's "Cite this repository" button.

## Acknowledgements (poster / paper template)

> Satellite data: Copernicus Sentinel-2 (ESA) and Landsat (USGS), accessed via Google Earth Engine. Glacier outlines: Randolph Glacier Inventory 7.0 (Pfeffer et al., 2014). In-situ validation: WGMS reference glacier Tuyuksu. Deep learning pipeline: GlacierNET-KZ (Nurlanuly, 2026).
