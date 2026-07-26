# Resilience-aware stress-test contract

## Scope

The resilience layer asks how a declared basin model responds to standardised
perturbations. It does not predict an event date and does not convert an
uncalibrated threshold crossing into a GLOF probability.

The implemented loop is:

`observe → assimilate → stress → classify pathway → prioritise observation`.

## State dependence

A stress model may depend on posterior state variables such as water level,
freeboard or outlet capacity. All required variables must exist in the
assimilated state. Missing values stop the calculation; the system does not
replace them with an undocumented mean.

The first baseline is intentionally transparent:

\[
s(x,u)=b + \beta_x^\top x + \beta_u^\top u.
\]

A scenario crosses the model transition surface when
`s(x,u) >= threshold`. The smallest declared scenario cost among crossing
scenarios is the model-defined resilience margin. Scenario cost and units must
be declared by the experiment. They are not automatically comparable across
studies.

## Calibration states

- `unvalidated_model_screening`: coefficients or thresholds have not passed an
  external retrospective calibration.
- `calibrated_model_screening`: a calibration reference is supplied. This
  still does not make the output an official warning.
- `external_calibration_required`: the stress surface can be explored, but a
  physical resilience class is withheld.
- `right_censored`: no tested scenario crossed the model surface; this means
  “above the tested surface,” not “safe.”

## Resilience diagnostics

The baseline includes monthly climatology residuals, lag-1 autocorrelation,
variance, observed recovery time, response gain and local-model spectral
radius. Each diagnostic retains its limitations:

- lag-1 correlation cannot independently prove critical slowing down;
- response gain is association unless the design supports causal inference;
- missing or irregular observations can bias diagnostics;
- spectral radius describes the supplied local model, not nature directly;
- unrecovered responses are right-censored rather than discarded.

## Failure Genome

Failure Genome is an explainable rule-based hypothesis:

- filling/overtopping/erosion;
- outlet degradation;
- slope impact wave;
- glacier collapse wave.

It is produced from the critical scenario’s active stress variables. It is a
review taxonomy, not a diagnosed physical failure mechanism.

## Two priorities

Potential-hazard priority uses current anomaly, model-defined resilience
vulnerability and potential consequence. Observation priority uses missing
evidence, relative uncertainty, staleness and expected Value of Information.

Uncertainty does not increase the potential-hazard score. It increases the need
to acquire evidence. Neither priority is an event probability.

## Evidence required for scientific claims

1. Source-reviewed event and non-event basin histories.
2. Immutable pre-event observation snapshots.
3. Seasonal and weather-conditioned null tests.
4. Artificial missingness and cadence sensitivity experiments.
5. Frozen spatial and temporal external splits.
6. Calibration of coefficients, transition surfaces and scenario costs.
7. Comparison against lake area, static susceptibility, ML classifier and Risk
   Twin without stress testing.
8. Basin-level confidence intervals for lead time, false alerts, recall,
   decision regret, abstention and observation cost.
