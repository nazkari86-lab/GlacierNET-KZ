"""Active Cryosphere Risk Twin scientific baseline.

This package exposes decision-support primitives. It does not issue official
warnings or calibrated GLOF probabilities.
"""

from .assimilation import assimilate_many, assimilate_observation
from .brief import build_daily_decision_brief
from .cascade import CascadeGraph, default_glacial_lake_cascade
from .decision import ObservationAction, assess_decision_support, rank_observations
from .failure_genome import classify_failure_genome
from .priorities import priority_pair
from .resilience import lag1_diagnostic, local_stability, recovery_times, response_gain
from .schemas import BasinState, GaussianEstimate, Observation, StateVariable
from .stress import LinearStressModel, StressScenario, run_stress_surface
from .uncertainty import (
    propagate_uncertainty_chain,
    sensitivity_summary,
    split_conformal_interval,
    split_conformal_radius,
)

__all__ = [
    "BasinState",
    "CascadeGraph",
    "GaussianEstimate",
    "LinearStressModel",
    "Observation",
    "ObservationAction",
    "StateVariable",
    "StressScenario",
    "assess_decision_support",
    "assimilate_many",
    "assimilate_observation",
    "build_daily_decision_brief",
    "classify_failure_genome",
    "default_glacial_lake_cascade",
    "lag1_diagnostic",
    "local_stability",
    "priority_pair",
    "rank_observations",
    "recovery_times",
    "response_gain",
    "run_stress_surface",
    "propagate_uncertainty_chain",
    "sensitivity_summary",
    "split_conformal_interval",
    "split_conformal_radius",
]
