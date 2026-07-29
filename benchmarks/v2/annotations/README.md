# Benchmark v2 Gold Annotation Queue

This folder is the control plane for expert labels; it does not contain large
imagery or polygons.

## Machine-assisted bootstrap pack

For immediate technical QA, create a deterministic RGI-derived pack without
pretending it is expert truth:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/build_machine_assisted_label_pack.py
```

It writes `annotations/machine_assisted/` with GeoPackages for 2022–2024, a
task queue, SHA-256 digests and an explicit `provisional_not_gold` tier. These
geometries may support annotation, map review and engineering tests, but they
must never be used to claim independent accuracy or external generalisation.

Verify the pack after moving or regenerating it:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/validate_machine_assisted_label_pack.py
```

## Enhanced multi-evidence QGIS pack

The stronger local bootstrap is built directly from each annual 11-channel
Sentinel-2 GeoTIFF. It combines annual spectral evidence, three-year
consistency and an RGI spatial prior, while placing every disagreement into a
separate visual-review layer:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/build_enhanced_annotation_pack.py

bash scripts/run_qgis_annotation_project.sh

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/finalize_qgis_annotation_project.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/render_annotation_qa.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/validate_enhanced_annotation_pack.py
```

Open `enhanced_provisional/GlacierNET-KZ_Annotation_Workspace.qgz`. Generated
labels are read-only references; save any manual edits into a new pass
GeoPackage. The enhanced pack remains provisional until independent annotation
and adjudication are complete.

## Leakage-safe ML export

Build a compact model-development dataset from only the strongest provisional
labels:

```bash
/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/build_enhanced_provisional_training_dataset.py

/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python \
  scripts/validate_enhanced_provisional_training_dataset.py
```

The export is written to
`data/processed/patches/enhanced_provisional_spatial_holdout`. Every year of
one glacier stays in one split, explicit pixel weights down-weight review
zones, and medium/low cases remain excluded in the active-review queue.
Validation/test scores from this dataset are internal development evidence,
not gold-label or external-generalisation accuracy.

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
