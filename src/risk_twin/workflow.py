"""End-to-end baseline workflow shared by CLI and API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .assimilation import assimilate_many
from .brief import build_daily_decision_brief
from .cascade import default_glacial_lake_cascade
from .decision import ObservationAction, assess_decision_support, counterfactual_screen, rank_observations
from .failure_genome import classify_failure_genome
from .priorities import priority_pair
from .schemas import Observation, StateVariable
from .stress import LinearStressModel, StressScenario, run_stress_surface


def _variable(value: str | StateVariable) -> StateVariable:
    return value if isinstance(value, StateVariable) else StateVariable(value)


def _datetime(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_basin_payload(payload: dict[str, Any]) -> dict[str, Any]:
    basin_id = str(payload["basin_id"])
    observations = [
        Observation(
            observation_id=str(item["observation_id"]),
            basin_id=basin_id,
            variable=_variable(item["variable"]),
            value=float(item["value"]),
            uncertainty_std=float(item["uncertainty_std"]),
            timestamp=_datetime(item["timestamp"]),
            sensor=str(item["sensor"]),
            quality_flags=tuple(item.get("quality_flags", [])),
            spatial_support=str(item.get("spatial_support", "basin_screening")),
        )
        for item in payload.get("observations", [])
    ]
    state = assimilate_many(basin_id, observations)
    required = {
        _variable(value)
        for value in payload.get(
            "required_variables",
            [
                StateVariable.LAKE_AREA.value,
                StateVariable.WATER_LEVEL.value,
                StateVariable.FREEBOARD.value,
                StateVariable.DAM_STABILITY.value,
                StateVariable.OUTLET_CAPACITY.value,
                StateVariable.CHANNEL_CAPACITY.value,
                StateVariable.EXPOSURE.value,
            ],
        )
    }
    weights = {
        _variable(key): float(value)
        for key, value in payload.get("decision_weights", {variable.value: 1.0 for variable in required}).items()
    }
    actions = []
    for item in payload.get("actions", []):
        targets = tuple(_variable(value) for value in item["target_variables"])
        variance = {_variable(key): float(value) for key, value in item["expected_observation_variance"].items()}
        actions.append(
            ObservationAction(
                action_id=str(item["action_id"]),
                label=str(item["label"]),
                target_variables=targets,
                expected_observation_variance=variance,
                cost=float(item.get("cost", 0)),
                latency_hours=float(item.get("latency_hours", 0)),
                available=bool(item.get("available", True)),
            )
        )
    action_ranking = rank_observations(
        state,
        actions,
        decision_weights=weights,
        missing_variance=float(payload.get("missing_variance", 1.0)),
        cost_weight=float(payload.get("cost_weight", 1.0)),
        latency_cost_per_hour=float(payload.get("latency_cost_per_hour", 0.0)),
    )
    support = assess_decision_support(
        state,
        required_variables=required,
        require_probability_calibration=bool(payload.get("require_probability_calibration", True)),
    )

    graph = default_glacial_lake_cascade(basin_id)
    scenario_paths = []
    for source in ("parent_glacier", "unstable_slope"):
        for path in graph.paths(source, "exposed_assets"):
            scenario_paths.append({"source": source, **graph.screen_path(state, path)})

    counterfactuals = None
    if payload.get("counterfactual_deltas"):
        counterfactuals = counterfactual_screen(
            state,
            {_variable(key): float(value) for key, value in payload["counterfactual_deltas"].items()},
            decision_weights=weights,
            missing_variance=float(payload.get("missing_variance", 1.0)),
        )

    stress_testing: dict[str, Any] = {
        "status": "model_and_scenarios_required",
        "resilience_margin": None,
        "safety_statement": "No resilience margin is inferred without an explicit stress model and scenario surface.",
    }
    failure_genome: dict[str, Any] = {
        "dominant": None,
        "alternatives": [],
        "status": "stress_test_required",
    }
    stress_model_payload = payload.get("stress_model")
    stress_scenario_payload = payload.get("stress_scenarios")
    if bool(stress_model_payload) != bool(stress_scenario_payload):
        raise ValueError("stress_model and stress_scenarios must be provided together")
    if stress_model_payload and stress_scenario_payload:
        model = LinearStressModel(
            coefficients={str(key): float(value) for key, value in stress_model_payload["coefficients"].items()},
            intercept=float(stress_model_payload["intercept"]),
            transition_threshold=float(stress_model_payload["transition_threshold"]),
            state_coefficients={
                str(key): float(value) for key, value in stress_model_payload.get("state_coefficients", {}).items()
            },
            calibrated=bool(stress_model_payload.get("calibrated", False)),
            calibration_reference=stress_model_payload.get("calibration_reference"),
            model_id=str(stress_model_payload.get("model_id", "linear_stress_screen_v1")),
            variable_units={
                str(key): str(value) for key, value in stress_model_payload.get("variable_units", {}).items()
            },
        )
        scenarios = [
            StressScenario(
                scenario_id=str(item["scenario_id"]),
                stresses={str(key): float(value) for key, value in item["stresses"].items()},
                physical_cost=float(item["physical_cost"]),
                provenance=tuple(str(value) for value in item.get("provenance", [])),
            )
            for item in stress_scenario_payload
        ]
        state_features = {variable.value: estimate.mean for variable, estimate in state.estimates.items()}
        stress_testing = run_stress_surface(model, scenarios, state_features=state_features)
        critical_id = stress_testing["resilience_margin"]["critical_scenario_id"]
        critical = next((scenario for scenario in scenarios if scenario.scenario_id == critical_id), None)
        failure_genome = classify_failure_genome(critical.stresses if critical else {})

    priority_inputs = payload.get("priority_inputs")
    priorities: dict[str, Any]
    if priority_inputs:
        available_estimates = list(state.estimates.values())
        mean_relative_uncertainty = (
            sum(estimate.std / max(abs(estimate.mean), estimate.std, 1e-9) for estimate in available_estimates)
            / len(available_estimates)
            if available_estimates
            else 1.0
        )
        best_voi = next(
            (float(item["model_based_uncertainty_reduction_fraction"]) for item in action_ranking if item["available"]),
            0.0,
        )
        priorities = priority_pair(
            current_anomaly=float(priority_inputs["current_anomaly"]),
            resilience_vulnerability=(
                float(priority_inputs["resilience_vulnerability"])
                if priority_inputs.get("resilience_vulnerability") is not None
                else None
            ),
            potential_consequence=float(priority_inputs["potential_consequence"]),
            missing_evidence_fraction=len(required - set(state.estimates)) / max(len(required), 1),
            relative_uncertainty=min(1.0, mean_relative_uncertainty),
            staleness=float(priority_inputs.get("staleness", 0.0)),
            expected_voi=min(1.0, max(0.0, best_voi)),
            resilience_model_calibrated=bool(stress_testing.get("model_calibrated", False)),
        )
    else:
        priorities = {
            "status": "priority_inputs_required",
            "hazard_priority": None,
            "observation_priority": None,
            "safety_statement": "No priority score is inferred from missing consequence/anomaly inputs.",
        }
    attention_score = 100 * len(required - set(state.estimates)) / max(len(required), 1)
    assessment = {
        "basin_id": basin_id,
        "attention_score": attention_score,
        "attention_score_semantics": "data-gap priority, not hazard probability",
        "significant_changes": [],
        "decision_support": support,
        "next_observation": next((item for item in action_ranking if item["available"]), None),
    }
    return {
        "system": "GlacierNET-KZ Active Cryosphere Risk Twin",
        "maturity": "research_baseline",
        "state": state.to_dict(),
        "cascade_graph": graph.to_dict(),
        "scenario_screening": scenario_paths,
        "observation_ranking": action_ranking,
        "decision_support": support,
        "counterfactual_screening": counterfactuals,
        "virtual_stress_test": stress_testing,
        "failure_genome": failure_genome,
        "priorities": priorities,
        "daily_decision_brief": build_daily_decision_brief([assessment]),
        "claims_not_allowed": [
            "official warning",
            "calibrated GLOF probability",
            "engineering intervention recommendation",
            "imminent event confirmation",
            "physical resilience margin without a calibrated stress model",
        ],
    }
