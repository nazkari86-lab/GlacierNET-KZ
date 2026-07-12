# Data Citation Guide

> Required citations when using GlacierNET-KZ in journal papers, technical reports, dashboards, or derived datasets. Follow each data provider's terms of use.

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

## Terrain and land-cover context

### Copernicus DEM GLO-30

```bibtex
@misc{copernicus_dem_glo30,
  author = {{European Space Agency}},
  title  = {Copernicus DEM GLO-30},
  year   = {2024},
  note   = {Accessed from the Copernicus DEM AWS Open Data registry},
  url    = {https://registry.opendata.aws/copernicus-dem/}
}
```

Used only as static terrain features (elevation, slope, aspect), not as labels.

### ESA WorldCover 2021 v200

```bibtex
@misc{esa_worldcover_2021,
  author = {{European Space Agency}},
  title  = {ESA WorldCover 10 m 2021 v200},
  year   = {2021},
  url    = {https://esa-worldcover.org/}
}
```

Used for land-cover context and hard-negative analysis, not as a glacier-outline label.

### GlaThiDa

```bibtex
@misc{wgms_glathida,
  author = {{World Glacier Monitoring Service}},
  title  = {Glacier Thickness Database (GlaThiDa)},
  year   = {2026},
  url    = {https://gitlab.com/wgms/glathida}
}
```

GlaThiDa is retained as an external thickness-supervision and transfer-learning reference. It is not used as local Kazakhstan segmentation ground truth.

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
  url     = {https://github.com/nazkari86-lab/GlacierNET-KZ},
  version = {0.2.0},
  license = {MIT}
}
```

Or use [`CITATION.cff`](../CITATION.cff) for GitHub's "Cite this repository" button.

## Acknowledgements Template

> Satellite data: Copernicus Sentinel-2 (ESA) and Landsat (USGS), accessed via Google Earth Engine. Glacier outlines: Randolph Glacier Inventory 7.0 (Pfeffer et al., 2014). Terrain context: Copernicus DEM GLO-30 and ESA WorldCover. In-situ validation: WGMS reference glacier Tuyuksu. Deep learning pipeline: GlacierNET-KZ (Nurlanuly, 2026).
