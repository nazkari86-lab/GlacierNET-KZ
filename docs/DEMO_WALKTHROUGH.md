# GlacierNET-KZ Demo Walkthrough

This is the public three-minute demonstration sequence for the local unified stack.

## Before the demo

Run `./scripts/start.sh`, open `http://localhost:8080/hub`, and keep this repository's
`results/` artifacts available. Use the built-in data; do not upload unpublished or sensitive
partner data during a public walkthrough.

## Three-minute flow

1. Open **Year Explorer** at `/explore`, select 2024, and show the local overlay, physically
   available method artifacts, source, quality score, and provenance link.
2. Compare 2000 with 2024 without uploading files. Point out the source and confidence fields.
3. Select 2015 and explain that it is a late-year Sentinel-2 TOA
   fallback and is excluded from strict Sentinel-2 SR model benchmarking.
4. Open **Glacier Registry**, select Central Tuyuksu, and show its RGI inventory card,
   16-year within-outline NDSI series, WGMS reference status, and downloadable evidence card.
5. Send the selected glacier to **AI Analysis** and show that the prompt and context are
   preloaded from verified local API data.
6. Open **Reports** and generate/export the decision report. It contains area change, trend,
   uncertainty and caveats for a non-technical stakeholder.
7. Use **Compare** only when demonstrating inference on a new multi-band GeoTIFF. The Year
   Explorer is the default path for already downloaded project data.
8. Open the MCP tools page and ask which years are high risk. The response must be interpreted
   alongside confidence and source-quality fields, not as an autonomous decision.

## Claims that are safe to make

- The project turns local satellite rasters into reproducible area, trend and decision-ready outputs.
- It contains real Sentinel-2 (2015-2024) and Landsat (2000-2013) local inputs for the study area.
- 2015 is explicitly labelled as a late-year TOA fallback.
- The evidence package and its provenance gates are reproducible locally.

## Claims to avoid

- Do not claim a production operational service, a completed external validation, or a confirmed
  water-supply forecast.
- Do not quote the 2020 random-patch F1 as temporal generalization accuracy.
- The current temporal holdout result is one-AOI validation against RGI-derived silver labels;
  do not present it as field accuracy, cross-region generalisation, or operational readiness.
