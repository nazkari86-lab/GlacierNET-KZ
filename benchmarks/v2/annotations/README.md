# Benchmark v2 Gold Annotation Queue

This folder is the control plane for expert labels; it does not contain large
imagery or polygons.

## Minimum publishable cohort

- 15–25 glaciers spanning small, medium, and large area classes.
- Three observation years per glacier where acceptable imagery exists.
- Two independent annotators who cannot see each other's geometry.
- A named third-person adjudication decision for every glacier-year.
- A SHA-256 digest of each final GeoPackage or raster label.
- Glacier-disjoint train, validation, and test groups.
- A geographically disjoint Zhetysu Alatau test cohort for external claims.

Copy `annotation_queue.template.csv`, fill one row per glacier-year, and keep
`annotation_status=pending` until both annotations and adjudication exist.
Then build a manifest:

```bash
python scripts/build_glacier_holdout_manifest.py \
  --metadata data/gold/metadata/glacier_years.csv \
  --output benchmarks/v2/manifests/glacier_holdout.json
```

The command fails closed if annotators are not distinct, adjudication is
missing, or a final label has no valid checksum. A generated split is a
reproducible data split, not proof that the labels are scientifically correct.
