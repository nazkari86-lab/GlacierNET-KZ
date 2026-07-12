# GlacierNET-KZ Demo Walkthrough

This is the public three-minute demonstration sequence for the local unified stack.

## Before the demo

Run `./scripts/start.sh`, open `http://localhost:8080/hub`, and keep this repository's
`results/` artifacts available. Use the built-in data; do not upload unpublished or sensitive
partner data during a public walkthrough.

## Three-minute flow

1. Open **Dashboard** and show the 2000-2024 glacier-area history for the Ili Alatau study area.
2. Point out the source and confidence columns. Explain that 2015 is a late-year Sentinel-2 TOA
   fallback and is excluded from strict Sentinel-2 SR model benchmarking.
3. Open **Reports** and generate/export the decision report. It contains area change, trend,
   uncertainty and caveats for a non-technical stakeholder.
4. Open **Compare** to show the NDSI, Random Forest and U-Net method comparison. State that the
   published 2020 patch metrics are not a substitute for temporal generalization testing.
5. Show the RF importance chart: NDSI and NDWI are the highest-ranked baseline features.
6. Open the MCP tools page and ask which years are high risk. The response must be interpreted
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
- Do not present the capped 2016-2024 temporal benchmark as successful: the preliminary run did
  not converge on the 2023 validation year and is retained only as a negative benchmark log.
