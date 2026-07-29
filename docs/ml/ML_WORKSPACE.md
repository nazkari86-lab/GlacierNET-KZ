# Glacier-first ML Workspace

The ML Workspace is the primary intelligence workflow in GlacierNET-KZ:

1. Select a physical RGI 7.0 glacier.
2. Select a model-compatible local year.
3. The API reads only a bounded geographic crop from the multi-gigabyte Sentinel-2 composite.
4. It aligns terrain and, where available, year-matched Sentinel-1 VV/VH.
5. The trusted temporal model runs with its validation-selected threshold and optional flip TTA.
6. The service isolates the connected glacier component that overlaps the selected RGI object.
7. The UI displays the ML boundary, RGI reference, probability, predictive entropy and review priority.
8. A stable case ID links the exact evidence package into the Active Cryosphere Risk Twin.

## API

- `GET /api/ml/readiness`
- `POST /api/ml/glaciers/{rgi_id}/analyze`
- `GET /api/ml/cases`
- `GET /api/ml/cases/{case_id}`

Example request:

```json
{
  "year": 2024,
  "model_name": "temporal_s2_terrain_s1",
  "use_tta": true,
  "context_m": 400,
  "refresh": false
}
```

## Evidence semantics

`rgi_overlap_iou` is agreement with a fixed inventory geometry, not independent
accuracy. Predictive entropy is a model review signal, not a calibrated hazard
or event probability. Every manifest lists allowed and prohibited claims.
