"""Decision support: VOI ranking, abstention and counterfactual screening."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import BasinState, GaussianEstimate, StateVariable


@dataclass(frozen=True)
class ObservationAction:
    action_id: str
    label: str
    target_variables: tuple[StateVariable, ...]
    expected_observation_variance: dict[StateVariable, float]
    cost: float = 0.0
    latency_hours: float = 0.0
    available: bool = True

    def __post_init__(self) -> None:
        if self.cost < 0 or self.latency_hours < 0:
            raise ValueError("action cost and latency must be non-negative")
        if not self.target_variables:
            raise ValueError("action must target at least one state variable")
        for variable in self.target_variables:
            if self.expected_observation_variance.get(variable, 0) <= 0:
                raise ValueError(f"positive observation variance required for {variable.value}")


def _decision_loss(
    state: BasinState,
    weights: dict[StateVariable, float],
    *,
    missing_variance: float,
) -> float:
    return sum(
        weight * state.estimates.get(variable, GaussianEstimate(0, missing_variance, state.timestamp, 0)).variance
        for variable, weight in weights.items()
    )


def rank_observations(
    state: BasinState,
    actions: list[ObservationAction],
    *,
    decision_weights: dict[StateVariable, float],
    missing_variance: float = 1.0,
    cost_weight: float = 1.0,
    latency_cost_per_hour: float = 0.0,
) -> list[dict[str, Any]]:
    """Rank observations by expected variance-loss reduction minus declared cost."""
    if missing_variance <= 0:
        raise ValueError("missing_variance must be positive")
    current_loss = _decision_loss(state, decision_weights, missing_variance=missing_variance)
    results = []
    for action in actions:
        if not action.available:
            results.append(
                {
                    "action_id": action.action_id,
                    "label": action.label,
                    "available": False,
                    "net_value_of_information": None,
                    "reason": "action unavailable",
                }
            )
            continue
        reduction = 0.0
        contributions: dict[str, float] = {}
        for variable in action.target_variables:
            weight = decision_weights.get(variable, 0.0)
            prior = state.estimates[variable].variance if variable in state.estimates else missing_variance
            observation_variance = action.expected_observation_variance[variable]
            posterior = 1 / (1 / prior + 1 / observation_variance)
            contribution = weight * (prior - posterior)
            contributions[variable.value] = contribution
            reduction += contribution
        declared_cost = cost_weight * action.cost + latency_cost_per_hour * action.latency_hours
        net = reduction - declared_cost
        reduction_fraction = reduction / current_loss if current_loss > 0 else 0.0
        results.append(
            {
                "action_id": action.action_id,
                "label": action.label,
                "available": True,
                "target_variables": [variable.value for variable in action.target_variables],
                "expected_decision_loss_reduction": reduction,
                "model_based_uncertainty_reduction_fraction": reduction_fraction,
                "declared_cost": declared_cost,
                "net_value_of_information": net,
                "contributions": contributions,
                "interpretation": "model-based VOI estimate; not an empirical hazard-probability reduction",
            }
        )
    available = [row for row in results if row["available"]]
    available.sort(key=lambda row: (-float(row["net_value_of_information"]), str(row["action_id"])))
    unavailable = [row for row in results if not row["available"]]
    ranked = [*available, *unavailable]
    for rank, row in enumerate(available, start=1):
        row["rank"] = rank
    return ranked


def assess_decision_support(
    state: BasinState,
    *,
    required_variables: set[StateVariable],
    max_relative_std: float = 0.5,
    require_probability_calibration: bool = False,
) -> dict[str, Any]:
    reasons = []
    missing = required_variables - set(state.estimates)
    if missing:
        reasons.append("missing required state variables: " + ", ".join(sorted(item.value for item in missing)))
    uncertain = []
    for variable in required_variables & set(state.estimates):
        estimate = state.estimates[variable]
        relative_std = estimate.std / max(abs(estimate.mean), estimate.std, 1e-9)
        if relative_std > max_relative_std:
            uncertain.append(variable.value)
    if uncertain:
        reasons.append("high relative uncertainty: " + ", ".join(sorted(uncertain)))
    if require_probability_calibration and not state.probability_calibrated:
        reasons.append("hazard probability is not retrospectively calibrated")
    return {
        "abstain": bool(reasons),
        "status": "insufficient_evidence" if reasons else "screening_supported",
        "reasons": reasons,
        "official_warning": False,
        "safety_statement": "screening evidence only; requires specialist and authority review",
    }


def counterfactual_screen(
    state: BasinState,
    interventions: dict[StateVariable, float],
    *,
    decision_weights: dict[StateVariable, float],
    missing_variance: float = 1.0,
) -> dict[str, Any]:
    """Apply declared state deltas without claiming engineering effectiveness."""
    before = _decision_loss(state, decision_weights, missing_variance=missing_variance)
    changed = {}
    for variable, delta in interventions.items():
        estimate = state.estimates.get(variable)
        if estimate is None:
            changed[variable.value] = {"status": "unavailable", "reason": "state variable unobserved"}
        else:
            changed[variable.value] = {
                "before": estimate.mean,
                "after": estimate.mean + delta,
                "delta": delta,
                "variance_unchanged": estimate.variance,
            }
    return {
        "counterfactuals": changed,
        "decision_uncertainty_before": before,
        "decision_uncertainty_after": before,
        "interpretation": "counterfactual screening for prioritising detailed studies",
        "engineering_recommendation": False,
    }
