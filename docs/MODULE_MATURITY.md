# Module maturity and claim boundaries

This inventory separates validated product paths from research scaffolds. A
module being importable is not evidence that it is trained, scientifically
validated, or production-ready.

## Validated local paths

| Area | Evidence required |
|---|---|
| Data integrity | Local files, no Drive symlinks/placeholders/partials, manifest size and SHA-256 validation |
| Prediction export | GeoTIFF validation plus source, model, mask, environment, and output provenance hashes |
| Temporal benchmark | Leakage-free year holdout, saved-model hash, manifest hash, explicit claim limits |
| API core | Non-experimental API tests, auth/security middleware tests, type checks |
| Web application | Unit tests, lint, production build, production dependency audit |

## Research scaffolds

The following modules are prototypes or research utilities and are not part of
the validated scientific claim surface:

`anomaly`, `callbacks`, `clustering`, `datasets`, `diffusion_model`,
`distributed_training`, `domain_adaptation`, `evaluation`,
`feature_engineering`, `federated_learning`, `graph_neural_network`,
`interpretability`, `multi_task_learning`, `postprocessing`, `reporting`,
`schedulers`, `self_supervised`, `time_series`, `uncertainty`, and
`vision_transformer`.

Some have unit tests and some remain low-coverage. None should be described as
validated merely because an MCP wrapper exists. MCP tools that can construct an
untrained model or produce synthetic demonstration data are disabled by default
through `GLACIERKZ_ENABLE_UNVALIDATED_RESEARCH_TOOLS`. Enabling that variable is
for local research demonstrations only and does not upgrade evidence maturity.

## Coverage policy

CI measures the entire Python source and API package, including research
scaffolds, and currently enforces a 35% repository-wide floor. This lower bound
is intentionally not presented as strong coverage. It is a ratchet against
regression while tests are added to the low-coverage research surface. Core API
paths have materially higher per-file coverage, visible in the XML/terminal
coverage report.

No module is omitted from the repository-wide metric solely to make the total
look better.
