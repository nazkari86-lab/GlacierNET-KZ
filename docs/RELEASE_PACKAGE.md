# Local Release Package

## Contents

- Public project overview: `README.md`
- Reproduction procedure: `docs/REPRODUCIBILITY.md`
- Demo script: `docs/DEMO_WALKTHROUGH.md`
- Architecture and API references: `docs/ARCHITECTURE.md`, `docs/API_REFERENCE.md`
- Data provenance and citation: `results/data_quality_report.json`, `results/decision_readiness_summary.json`, `docs/DATA_CITATION.md`
- Decision-ready tables: `results/tables/decision_ready_area_timeseries.csv` and `results/tables/year_quality_scores.csv`
- Baseline interpretability: `results/tables/random_forest_feature_importance.csv`
- Real-data EDA summary: `results/tables/eda_sentinel2_2020.csv`

## Release gate

Run the following before creating a GitHub release:

```bash
python scripts/build_project_evidence_package.py
python scripts/verify_local_release_package.py
python -m pytest tests/ -q --no-cov
```

The first command rebuilds the reproducible evidence artifacts. The second checks that the
release documentation and public derived outputs are present. Large rasters, patch arrays and
weights stay out of Git and must be shared separately with checksums or rebuilt locally.

## Required manual publication steps

1. Commit the verified source, documentation and lightweight result tables.
2. Create a Git tag and GitHub release from the verified commit.
3. Attach a small public demo dataset or link an external artifact repository with checksums.
4. Add the published dashboard/API URL only after deployment smoke tests pass.

This package deliberately does not claim that an external expert review, stakeholder pilot, LOI,
or public deployment already exists.
