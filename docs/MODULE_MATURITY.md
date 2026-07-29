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

`anomaly`, `datasets`, `diffusion_model`, `distributed_training`, `evaluation`,
`federated_learning`, `graph_neural_network`, `multi_task_learning`,
`postprocessing`, `reporting`, `schedulers`, `self_supervised`, `time_series`,
`uncertainty`, and `vision_transformer`.

Some have unit tests and some remain low-coverage. None should be described as
validated merely because it is importable. The public MCP catalog contains only
physical-data readers and the trusted glacier-first inference workflow.
Synthetic/random fallbacks and wrappers around untrained architectures were
removed rather than hidden behind a feature flag.

## Coverage policy

CI measures the entire Python source and API package, including research
scaffolds. It enforces both a 45% repository-wide floor and a 55% production
scope floor. The machine-readable classification is
`config/coverage_scopes.json`; CI publishes the full JSON, XML, and scoped
report as one evidence artifact. Research coverage remains visible as its own
number and is never subtracted from the repository-wide metric.

No module is omitted from the repository-wide metric solely to make the total
look better.

## Active Cryosphere Risk Twin

`src/risk_twin` is a tested **research baseline**, separate from both the
validated segmentation core and the older unvalidated scaffolds. It currently
provides typed partial observations, scalar Gaussian/Kalman assimilation,
auditable provenance, a directed acyclic cascade graph, model-based Value of
Information ranking, fail-closed abstention, counterfactual screening, event
replay truncation, finite-sample split-conformal scalar intervals, declared
ensemble uncertainty propagation and decision-focused evaluation metrics.

The resilience-aware extension adds observed recovery-time diagnostics,
response gain, lag-1/variance diagnostics with gap auditing, local-model
spectral radius, state-dependent virtual stress surfaces, model-defined
resilience margins, Failure Genome hypotheses and separate potential-hazard
and observation priorities. Its contract is documented in
[RESILIENCE_STRESS_TEST.md](RESILIENCE_STRESS_TEST.md).

The conformal helper currently covers scalar quantities such as area or water
level. It is not yet a calibrated morphological inner/outer boundary set.
Ensemble propagation executes explicitly supplied stage models; it does not
pretend that an unvalidated transform is a physical flood simulator.
Likewise, an uncalibrated stress threshold produces
`unvalidated_model_screening`, not a physical resilience class.

The cascade `evidence_strength` value measures variable coverage penalised by
relative uncertainty. It is not an event probability. The module does not
currently provide calibrated GLOF probabilities, field-validated engineering
states, an official warning, or an intervention recommendation.

The [Central Asia Cascade Benchmark](../benchmarks/central_asia_cascade/protocol.md)
defines the evidence required to upgrade these claims. Its structural validator
passes with `--allow-incomplete`; the strict gate intentionally fails until
source-reviewed events, non-event controls, immutable pre-event snapshots and
an external-region cohort are present.
