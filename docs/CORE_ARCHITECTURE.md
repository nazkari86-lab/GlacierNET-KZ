# GlacierNET-KZ core architecture

The project deliberately keeps one evidence path:

`physical local data -> registered model or deterministic baseline -> persisted artifact -> API -> map/AI context`

## Retained product core

| Capability | Source of truth | User surface |
|---|---|---|
| Glacier registry | Local RGI 7.0 study-area files | `/glaciers`, `/ml`, MCP |
| Annual inspection | Local result tables and prediction rasters | `/analysis`, map layers, MCP |
| Glacier segmentation | Trusted temporal model artifacts plus Sentinel-2, terrain, and optional Sentinel-1 | `/ml`, persisted ML cases, MCP |
| Risk Twin context | Local lakes, GLOF inventory, HydroRIVERS/HydroBASINS, terrain, JRC water, ERA5-Land, GHSL/OSM | `/risk-twin`, MCP |
| Evidence handoff | Versioned manifests, hashes, caveats, downloadable artifacts | `/ml`, `/jury`, API |

## Deliberately excluded

- Random masks, random anomaly scores, synthetic confidence values, and
  untrained architecture predictions.
- Separate C, C++, Go, Java, and .NET prototypes that had no production caller,
  benchmark advantage, or reusable artifact.
- Python modules with no import, route, test, CLI, notebook, or documented
  reproducibility role.

Research ideas are promoted only when they have a real dataset contract, a
measured evaluation protocol, an API/product consumer, and a fail-closed claim
boundary. This keeps the project understandable without discarding physical
data, trained artifacts, reproducibility records, or the tested Risk Twin
research baseline.
