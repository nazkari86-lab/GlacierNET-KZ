# Reproducibility Guide

This guide reproduces the evidence that is currently supported by checked
artifacts. It does not treat exploratory historical tables as published facts.

## Fast code check

```bash
git clone https://github.com/nazkari86-lab/GlacierNET-KZ.git
cd GlacierNET-KZ
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev,api]"
python notebooks/_synthetic_smoke_test.py
python notebooks/_unet_smoke_test.py
pytest tests/ glacierkz-api/tests/ -q -m "not experimental"
```

## Current reproducible scientific result

The supported result is a 2024 temporal holdout over one Ile Alatau AOI with
RGI-derived **silver** labels. Thresholds were selected on validation data and
then frozen for the test set.

| Model | Threshold | Hard Dice | Hard IoU | Precision | Recall | Area error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S2 + terrain, 14 channels | 0.2 | 0.8746 | 0.7771 | 0.9508 | 0.8097 | −49.8204 km² |
| Compact S2 + terrain control | 0.3 | 0.8937 | 0.8078 | 0.9224 | 0.8668 | −4.7873 km² |
| Compact control + S1 VV/VH | 0.5 | **0.9036** | **0.8242** | 0.9252 | **0.8830** | **−3.6214 km²** |

The compact Sentinel-1 model improves hard IoU, recall, and absolute area error
relative to its same-patch control under independently validation-calibrated
thresholds. This supports a one-AOI feature-ablation result only.

## Exact evaluation commands

The trained SavedModels and processed arrays are large local artifacts. Verify
their checksums against `models/trusted_artifacts.json` and the patch manifests,
then run:

```bash
python scripts/evaluate_temporal_benchmark.py \
  --output results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json

python scripts/evaluate_temporal_benchmark.py \
  --patches-dir data/processed/patches/sentinel2_terrain_control_year_holdout_2017_2024 \
  --model models/unet_best_sentinel2_terrain_control_year_holdout_2017_2024 \
  --output results/ablation_unet_sentinel2_terrain_control_2017_2024.json

python scripts/evaluate_temporal_benchmark.py \
  --patches-dir data/processed/patches/sentinel2_terrain_s1_year_holdout_2017_2024 \
  --model models/unet_best_sentinel2_terrain_s1_year_holdout_2017_2024 \
  --output results/ablation_unet_sentinel2_terrain_s1_2017_2024.json

python scripts/build_benchmark_v2_tables.py
python scripts/validate_benchmark_v2.py --allow-incomplete
python scripts/validate_provisional_cohorts.py
python scripts/validate_claims_registry.py
python scripts/run_quality_gates.py
```

`validate_benchmark_v2.py` without `--allow-incomplete` is the strict scientific
gate. It must remain blocked until adjudicated glacier-level gold labels and a
disjoint Zhetysu Alatau test set exist.

## Superseded exploratory claims

Earlier documentation quoted a 2000–2020 area loss, a −12.7 km²/year trend, and
a 2050 area forecast. Those values came from mixed sensors and non-uniform
segmentation methods and are **not current validated findings**.

The current decision-readiness series has slope +3.1025 km²/year, R² 0.0398,
and p=0.667866. It is statistically insignificant and cannot support a glacier
change or 2050 forecast claim. Forecasting code remains available as an
exploratory tool, but its output is not operational evidence.

## Data and provenance

| Dataset | Source | Role |
| --- | --- | --- |
| Sentinel-2 L2A | Copernicus / Earth Engine | optical imagery |
| Sentinel-1 GRD | Copernicus / Earth Engine | controlled radar ablation |
| RGI 7.0 region 13 | GLIMS/NSIDC | silver reference labels |
| WGMS Tuyuksu | WGMS | limited external area context |
| DEM/terrain derivatives | documented in data manifest | ancillary channels |

The study AOI is 76.5–77.5°E, 42.8–43.2°N. Every release-grade artifact must
carry a source path, byte size, SHA-256 digest, split definition, label-quality
tier, and software revision. Run `scripts/validate_data_manifest.py` without
exceptions for the strict local-data gate.

## Remaining evidence boundary

The machine-readable `benchmarks/v2/claims_registry.json` is the source of
truth for supported, provisional, refuted, and blocked claims. The repository
does not yet establish:

- independent expert-label accuracy;
- cross-region generalisation;
- field validation;
- calibrated GLOF probability or operational warning performance.

Automatic provisional cohorts now include glacier-level paired confidence
intervals and boundary metrics, but remain non-independent RGI-silver evidence.
The annotation queue and fail-closed builders in `benchmarks/v2/annotations/`
make the remaining gaps executable work rather than undocumented promises.

## CryoGenesis Release 1

CryoGenesis builds a retrospective matched-glacier cohort from physical local
RGI, Copernicus DEM-derived inventory attributes, ERA5-Land, and declared
annual masks. It never downloads data or substitutes a fixture in physical
mode.

```bash
python scripts/build_cryogenesis_cohort.py --preflight

python scripts/build_cryogenesis_cohort.py \
  --cohort-id ile-2016-2024-v1 \
  --anchor-year 2016 \
  --outcome-year 2024 \
  --output-root results/cryogenesis/current

python scripts/validate_cryogenesis_passports.py \
  results/cryogenesis/current
```

The saved bundle contains `manifest.json`, `features.parquet`,
`eligibility.csv`, `source_assets.json`, `build_report.json`,
`checksums.sha256`, and one passport per target. Every source and output is
content-addressed. Matching fails closed on post-anchor features, split
crossing, missing required values, hard-caliper violations, or insufficient
comparators.

The engineering fixture is invoked only with `--feature-fixture` and always
reports `scientific_readiness: insufficient_cohort_size`. It is not product or
scientific evidence.

API verification:

```bash
pytest glacierkz-api/tests/test_cryogenesis.py -q --no-cov
curl -fsS http://127.0.0.1:8000/api/cryogenesis/status
curl -fsS http://127.0.0.1:8000/api/cryogenesis/discoveries
```
