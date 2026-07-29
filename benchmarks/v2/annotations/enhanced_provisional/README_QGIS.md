# GlacierNET-KZ enhanced provisional annotation workspace

These files are machine-assisted starting geometries, **not gold labels**.

## Open in QGIS

1. Add the original annual Sentinel-2 stacks:
- `data/raw/sentinel2/sentinel2_2022.tif`
- `data/raw/sentinel2/sentinel2_2023.tif`
- `data/raw/sentinel2/sentinel2_2024.tif`
2. For each year add `enhanced_labels_YYYY.gpkg` layer `glacier_labels`.
3. Add `enhanced_labels_YYYY.gpkg` layer `review_zones`.
4. Load `labels.qml` on label layers and `review_zones.qml` on review layers.
5. Display Sentinel bands B4/B3/B2 as RGB, then inspect NDSI (band 8), DEM,
   Sentinel-1 and adjacent years before editing.
6. Filter `review_priority >= 50` first. Every amber zone requires visual QA.
7. Save human work into a new `pass_1.gpkg`; never overwrite these generated files.

## Meaning of the layers

- `glacier_labels`: conservative annual candidate connected to the target RGI body.
- `review_zones`: boundary disagreement, ambiguous spectral evidence, missing pixels,
  and RGI-vs-annual differences that require a person.
- `label_classes_YYYY.tif`: 0 background, 1 provisional glacier, 2 review-only.

The source RGI geometry is a spatial prior, not annual ground truth. Existing
`data/processed/masks/mask_YYYY.tif` files were excluded because their SHA-256
digests are identical across years.
