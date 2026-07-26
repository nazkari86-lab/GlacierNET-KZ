# GlacierNET-KZ Gold Dataset Card

## Current status

`NOT YET COLLECTED`

The repository currently contains RGI-derived silver labels for one AOI. It
does not yet contain independently reviewed gold polygons or a completed
Zhetysu Alatau external test set. This card is an evidence contract, not a claim
that those assets exist.

## Intended dataset

- Regions: Ile Alatau and Zhetysu Alatau
- Sensors: Sentinel-2 Surface Reflectance; paired Sentinel-1 VV/VH where used
- Season: July–September, August preferred
- Target size: 15–25 primary-region glaciers plus 5–10 external-region glaciers
- Years: three comparable years, initially 2017, 2020, and 2024
- Classes: clean ice and debris-covered ice
- Label geometry: georeferenced polygons in GeoPackage or GeoJSON

## Required glacier-year record

```json
{
  "glacier_id": "KZ_ILE_001",
  "region": "Ile Alatau",
  "year": 2024,
  "image_date": "2024-08-17",
  "sensor": "Sentinel-2",
  "product_id": null,
  "cloud_fraction": 0.01,
  "shadow_fraction": null,
  "off_glacier_snow_fraction": null,
  "nodata_fraction": null,
  "snow_condition": "low_snow",
  "ice_type": "clean",
  "annotation_version": 2,
  "confidence": "high",
  "intra_annotator_iou": null,
  "caveats": []
}
```

`null` fields must be completed before release. A glacier-year with missing
scene QA, image date, annotation pass, or intra-annotator agreement cannot enter
the gold test set.

## Provenance and licensing

Record source product IDs, acquisition dates, download URLs, checksums,
processing commands, annotator ID, annotation timestamps, adjudication notes,
and upstream licences. Personal credentials and provider tokens must never be
stored in the dataset.

## Known limitations

- A single annotator measured twice does not replace inter-annotator agreement.
- RGI polygons are reference inventory data, not independent contemporary gold
  segmentation.
- Three years do not establish a climate trend.
- Cross-region performance must be reported separately from temporal holdout.

## Release checklist

- [ ] 15–25 Ile Alatau glaciers have two annotation passes.
- [ ] 5–10 Zhetysu Alatau glaciers form a fully external test region.
- [ ] All scenes pass the frozen acquisition protocol.
- [ ] Every glacier-year has `intra_annotator_iou`.
- [ ] Split manifests are disjoint by `glacier_id`.
- [ ] Dataset licence and upstream licences are documented.
- [ ] A named expert review is recorded, or its absence is stated explicitly.
