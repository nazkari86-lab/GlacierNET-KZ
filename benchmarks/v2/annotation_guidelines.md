# Gold Annotation Guidelines

## Tool and geometry

Use QGIS and preserve source CRS. Store polygons in a GeoPackage with one row
per glacier-year and the metadata fields from `dataset_card.md`. Do not annotate
from rescaled screenshots when the source GeoTIFF is available.

## Scene acceptance

Use July–September Surface Reflectance imagery, with August preferred. Reject or
replace scenes with cloud over the target, substantial haze, severe seasonal
snow ambiguity, missing pixels, or inconsistent resolution/CRS/bands.

## Boundary rules

1. Trace the visible glacier boundary at a consistent working scale.
2. Include connected clean and debris-covered glacier ice.
3. Exclude seasonal snow that is not connected to a defensible glacier body.
4. Use terrain, Sentinel-1, and adjacent years only as supporting context; do
   not copy an older inventory boundary blindly.
5. Mark uncertain segments in `caveats` and lower `confidence`.
6. Preserve nunataks and internal rock exclusions where visible.

## Repeatability protocol

1. Complete annotation pass 1 and freeze it.
2. Wait 5–7 days.
3. Complete pass 2 from the imagery without displaying pass 1.
4. Rasterise both polygons on the same grid and calculate
   `intra_annotator_iou`.
5. Review disagreements, recording whether the final polygon uses pass 1, pass
   2, their geometric combination, or manual adjudication.
6. Never overwrite either original pass.

Suggested interpretation:

| Intra-annotator IoU | Action |
| --- | --- |
| ≥0.90 | accept after visual QA |
| 0.80–0.90 | review disagreement zones |
| <0.80 | repeat or request independent review |

These thresholds are workflow gates, not proof of label correctness.

## File layout

```text
data/gold/
  imagery/
  annotations/pass_1.gpkg
  annotations/pass_2.gpkg
  annotations/final.gpkg
  metadata/glacier_years.csv
  qa/intra_annotator.csv
```

Large imagery and annotation artifacts should be versioned through a
checksum-based data release, not committed directly to Git.
