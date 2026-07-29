# CryoGenesis Release 1 Protocol

CryoGenesis Release 1 is a retrospective, leakage-safe comparison of mapped
glacier area. It is not a causal model, mass-balance estimate, prospective
forecast, calibrated GLOF probability, operational warning, or intervention
recommendation.

## Frozen procedure

1. Register physical local RGI, Copernicus DEM-derived attributes, ERA5-Land
   and annual-mask assets by path, size and SHA-256.
2. Freeze all matching features at or before the anchor-year cutoff.
3. Exclude glaciers missing either anchor or outcome mapped-area observation.
   Require at least 0.01 km² of anchor support (100 pixels at 10 m) so pixel
   quantisation does not dominate tiny targets; never filter on outcome size.
4. Match only within the frozen split using declared robust-scaled features.
5. Return at most five deterministic comparators and abstain below three for
   the primary comparison.
6. Measure target minus weighted-comparator mapped-area change.
7. Emit one canonical, SHA-256-addressed Discovery Passport per target.
8. Keep all Release 2 mechanism records unscored.

The physical cohort is scientifically ready only with at least 30 eligible
glaciers. Smaller fixtures validate engineering, not scientific performance.
