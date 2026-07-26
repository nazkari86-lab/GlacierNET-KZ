from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.risk_twin.assimilation import assimilate_many
from src.risk_twin.cascade import CascadeEdge, default_glacial_lake_cascade
from src.risk_twin.decision import (
    ObservationAction,
    assess_decision_support,
    counterfactual_screen,
    rank_observations,
)
from src.risk_twin.evaluation import (
    decision_regret,
    gaussian_crps,
    interval_coverage,
    ranking_metrics,
    truncate_for_event_replay,
    warning_metrics,
)
from src.risk_twin.failure_genome import classify_failure_genome
from src.risk_twin.priorities import priority_pair
from src.risk_twin.resilience import (
    lag1_diagnostic,
    local_stability,
    monthly_climatology_residuals,
    recovery_times,
    response_gain,
)
from src.risk_twin.schemas import Observation, StateVariable
from src.risk_twin.stress import LinearStressModel, StressScenario, run_stress_surface
from src.risk_twin.uncertainty import (
    propagate_uncertainty_chain,
    sensitivity_summary,
    split_conformal_interval,
    split_conformal_radius,
)
from src.risk_twin.workflow import evaluate_basin_payload

UTC = timezone.utc


def observation(
    observation_id: str,
    variable: StateVariable,
    value: float,
    uncertainty: float,
    day: int,
) -> Observation:
    return Observation(
        observation_id=observation_id,
        basin_id="B001",
        variable=variable,
        value=value,
        uncertainty_std=uncertainty,
        timestamp=datetime(2025, 1, day, tzinfo=UTC),
        sensor="test sensor",
    )


def test_assimilation_is_time_ordered_auditable_and_reduces_variance():
    later = observation("lake-later", StateVariable.LAKE_AREA, 120, 4, 10)
    earlier = observation("lake-earlier", StateVariable.LAKE_AREA, 100, 5, 1)
    state = assimilate_many("B001", [later, earlier])
    estimate = state.estimates[StateVariable.LAKE_AREA]
    assert state.timestamp == later.timestamp
    assert estimate.variance < later.uncertainty_std**2
    assert estimate.source_ids == ["lake-earlier", "lake-later"]
    assert [row["observation"]["observation_id"] for row in state.provenance] == [
        "lake-earlier",
        "lake-later",
    ]


def test_observation_validation_rejects_non_finite_and_duplicate_evidence():
    with pytest.raises(ValueError, match="finite"):
        observation("bad", StateVariable.LAKE_AREA, float("nan"), 1, 1)
    duplicate = observation("same", StateVariable.LAKE_AREA, 1, 1, 1)
    with pytest.raises(ValueError, match="unique"):
        assimilate_many("B001", [duplicate, duplicate])


def test_assimilation_rejects_wrong_basin():
    item = observation("x", StateVariable.LAKE_AREA, 1, 1, 1)
    with pytest.raises(ValueError, match="basin_id"):
        assimilate_many("OTHER", [item])


def test_cascade_graph_finds_paths_and_rolls_back_cycle():
    graph = default_glacial_lake_cascade("B001")
    paths = graph.paths("parent_glacier", "exposed_assets")
    assert len(paths) == 1
    edge_count = len(graph.edges)
    with pytest.raises(ValueError, match="acyclic"):
        graph.add_edge(
            CascadeEdge(
                "exposed_assets",
                "parent_glacier",
                "invalid reverse dependency",
                (StateVariable.EXPOSURE,),
            )
        )
    assert len(graph.edges) == edge_count


def test_cascade_screening_never_returns_uncalibrated_probability():
    state = assimilate_many(
        "B001",
        [observation("velocity", StateVariable.GLACIER_VELOCITY, 12, 1, 1)],
    )
    graph = default_glacial_lake_cascade("B001")
    screened = graph.screen_path(state, graph.paths("parent_glacier", "exposed_assets")[0])
    assert 0 <= screened["evidence_strength"] <= 1
    assert screened["probability_interval"] is None
    assert "not_event_probability" in screened["evidence_scale"]


def test_voi_prioritises_larger_weighted_uncertainty_reduction():
    state = assimilate_many(
        "B001",
        [observation("lake", StateVariable.LAKE_AREA, 100, 10, 1)],
    )
    actions = [
        ObservationAction(
            "precise",
            "Precise lake observation",
            (StateVariable.LAKE_AREA,),
            {StateVariable.LAKE_AREA: 1},
        ),
        ObservationAction(
            "coarse",
            "Coarse lake observation",
            (StateVariable.LAKE_AREA,),
            {StateVariable.LAKE_AREA: 100},
        ),
        ObservationAction(
            "offline",
            "Unavailable field visit",
            (StateVariable.WATER_LEVEL,),
            {StateVariable.WATER_LEVEL: 0.1},
            available=False,
        ),
    ]
    ranked = rank_observations(
        state,
        actions,
        decision_weights={StateVariable.LAKE_AREA: 1},
    )
    assert [row["action_id"] for row in ranked] == ["precise", "coarse", "offline"]
    assert ranked[0]["rank"] == 1
    assert ranked[-1]["net_value_of_information"] is None


def test_abstention_is_fail_closed_and_counterfactual_is_not_recommendation():
    state = assimilate_many(
        "B001",
        [observation("lake", StateVariable.LAKE_AREA, 100, 2, 1)],
    )
    support = assess_decision_support(
        state,
        required_variables={StateVariable.LAKE_AREA, StateVariable.DAM_STABILITY},
        require_probability_calibration=True,
    )
    assert support["abstain"] is True
    assert support["official_warning"] is False
    scenario = counterfactual_screen(
        state,
        {StateVariable.LAKE_AREA: -10, StateVariable.DAM_STABILITY: 0.1},
        decision_weights={StateVariable.LAKE_AREA: 1},
    )
    assert scenario["engineering_recommendation"] is False
    assert scenario["counterfactuals"][StateVariable.DAM_STABILITY.value]["status"] == "unavailable"


def test_decision_focused_metrics_have_expected_semantics():
    ranking = ranking_metrics(["B2", "B1", "B3"], {"B1", "B4"}, ks=(1, 3))
    assert ranking["recall_at_1"] == 0
    assert ranking["recall_at_3"] == 0.5
    assert ranking["mean_reciprocal_rank"] == 0.5
    assert gaussian_crps(0, 1, 0) == pytest.approx(0.233694977)
    assert interval_coverage([(-1, 1), (0, 1)], [0, 2]) == 0.5
    assert decision_regret(2, [1, 5, 3]) == 3

    event_time = datetime(2025, 2, 1, tzinfo=UTC)
    warnings = warning_metrics(
        {"B001": event_time},
        [("B001", datetime(2025, 1, 20, tzinfo=UTC)), ("B002", event_time)],
        observation_years=2,
    )
    assert warnings["median_lead_time_days"] == 12
    assert warnings["false_alerts_per_basin_year"] == 0.5


def test_event_replay_hides_every_post_cutoff_observation():
    observations = [
        observation("old", StateVariable.LAKE_AREA, 1, 1, 1),
        observation("new", StateVariable.LAKE_AREA, 2, 1, 20),
    ]
    allowed, audit = truncate_for_event_replay(
        observations,
        event_time=datetime(2025, 2, 1, tzinfo=UTC),
        lead_time_days=20,
    )
    assert [item.observation_id for item in allowed] == ["old"]
    assert audit["post_cutoff_observation_ids"] == ["new"]
    assert audit["leakage_detected"] is False


def test_conformal_interval_uses_finite_sample_quantile_and_states_scope():
    residuals = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert split_conformal_radius(residuals, miscoverage=0.2) == 8
    interval = split_conformal_interval(5, residuals, miscoverage=0.2, lower_bound=0)
    assert interval["lower"] == 0
    assert interval["upper"] == 13
    assert "exchangeability" in interval["guarantee_scope"]


def test_uncertainty_chain_preserves_ensemble_and_counterfactual_boundary():
    propagated = propagate_uncertainty_chain(
        [1, 2, 3, 4],
        [
            ("area_to_volume_proxy", lambda values: values * 10),
            ("volume_to_screening_output", lambda values: values**0.5),
        ],
    )
    assert [stage["stage"] for stage in propagated["stages"]] == [
        "area_to_volume_proxy",
        "volume_to_screening_output",
    ]
    assert len(propagated["final_samples"]) == 4
    scenarios = sensitivity_summary([1, 2, 3], {"lower input": [0, 1, 2]})
    assert scenarios[0]["mean_delta"] == -1
    assert scenarios[0]["engineering_recommendation"] is False


def test_resilience_diagnostics_expose_sampling_and_causality_limits():
    timestamps = [datetime(2024 + index, 1, 1, tzinfo=UTC) for index in range(4)]
    climatology = monthly_climatology_residuals(timestamps, [10, 12, 14, 16])
    assert climatology["ready"] is True
    assert climatology["monthly_climatology"][1] == 13
    lag = lag1_diagnostic([1, 2, 3, 4], timestamps=timestamps)
    assert lag["lag1_autocorrelation"] == pytest.approx(1)
    assert lag["claim_status"] == "diagnostic_only"
    gain = response_gain([0, 1, 2, 3], [1, 3, 5, 7])
    assert gain["response_gain"] == pytest.approx(2)
    assert gain["claim_status"] == "association_not_causation"


def test_recovery_time_handles_observed_and_censored_events():
    timestamps = [datetime(2025, 1, day, tzinfo=UTC) for day in range(1, 8)]
    observed = recovery_times(timestamps, [1, 1, 1, 5, 3, 1, 1], [3])
    assert observed["events"][0]["recovery_time_days"] == 2
    censored = recovery_times(timestamps, [1, 1, 1, 5, 4, 3, 2], [3])
    assert censored["censored_events"] == 1
    assert censored["events"][0]["right_censored_at_days"] == 3


def test_local_stability_is_explicitly_only_a_model_diagnostic():
    stable = local_stability([[0.5, 0], [0, 0.7]])
    assert stable["spectral_radius"] == pytest.approx(0.7)
    assert stable["claim_status"] == "unvalidated_model_diagnostic"
    assert "does not predict" in stable["safety_statement"]


def test_stress_surface_requires_current_state_and_stays_fail_closed():
    model = LinearStressModel(
        coefficients={"rainfall_mm_24h": 0.02},
        state_coefficients={"water_level_m": 0.1},
        intercept=0,
        transition_threshold=1,
    )
    scenarios = [
        StressScenario("moderate", {"rainfall_mm_24h": 20}, 0.2),
        StressScenario("large", {"rainfall_mm_24h": 50}, 0.5),
    ]
    surface = run_stress_surface(model, scenarios, state_features={"water_level_m": 2})
    assert surface["resilience_margin"]["critical_scenario_id"] == "large"
    assert surface["resilience_margin"]["class"] == "external_calibration_required"
    assert surface["claim_status"] == "unvalidated_model_screening"
    with pytest.raises(ValueError, match="missing state features"):
        run_stress_surface(model, scenarios, state_features={})


def test_failure_genome_is_explainable_taxonomy():
    genome = classify_failure_genome(
        {
            "rainfall_mm_24h": 50,
            "temperature_anomaly_c": 3,
            "outlet_blockage_fraction": 0.4,
        }
    )
    assert genome["dominant"]["genome"] == "filling_overtopping_erosion"
    assert genome["alternatives"][0]["genome"] == "outlet_degradation"
    assert "not a diagnosed mechanism" in genome["interpretation"]


def test_uncertainty_changes_observation_priority_but_not_hazard_priority():
    low_uncertainty = priority_pair(
        current_anomaly=0.5,
        resilience_vulnerability=0.6,
        potential_consequence=0.7,
        missing_evidence_fraction=0.1,
        relative_uncertainty=0.1,
        staleness=0.1,
        expected_voi=0.1,
    )
    high_uncertainty = priority_pair(
        current_anomaly=0.5,
        resilience_vulnerability=0.6,
        potential_consequence=0.7,
        missing_evidence_fraction=0.1,
        relative_uncertainty=0.9,
        staleness=0.1,
        expected_voi=0.1,
    )
    assert low_uncertainty["hazard_priority"]["score"] == high_uncertainty["hazard_priority"]["score"]
    assert (
        low_uncertainty["observation_priority"]["score"]
        < high_uncertainty["observation_priority"]["score"]
    )


def test_end_to_end_payload_is_explicitly_screening_only():
    result = evaluate_basin_payload(
        {
            "basin_id": "B001",
            "observations": [
                {
                    "observation_id": "lake",
                    "variable": "lake_area_m2",
                    "value": 100,
                    "uncertainty_std": 2,
                    "timestamp": "2025-01-01T00:00:00Z",
                    "sensor": "Sentinel-2",
                }
            ],
            "actions": [
                {
                    "action_id": "water-level",
                    "label": "Acquire water level",
                    "target_variables": ["water_level_m"],
                    "expected_observation_variance": {"water_level_m": 0.04},
                }
            ],
        }
    )
    assert result["maturity"] == "research_baseline"
    assert result["decision_support"]["abstain"] is True
    assert result["daily_decision_brief"]["safety_statement"]
    assert "official warning" in result["claims_not_allowed"]


def test_end_to_end_resilience_cycle_uses_posterior_state():
    result = evaluate_basin_payload(
        {
            "basin_id": "B001",
            "observations": [
                {
                    "observation_id": "level",
                    "variable": "water_level_m",
                    "value": 2,
                    "uncertainty_std": 0.1,
                    "timestamp": "2025-01-01T00:00:00Z",
                    "sensor": "field gauge",
                }
            ],
            "stress_model": {
                "coefficients": {"rainfall_mm_24h": 0.02},
                "state_coefficients": {"water_level_m": 0.1},
                "intercept": 0,
                "transition_threshold": 1,
            },
            "stress_scenarios": [
                {
                    "scenario_id": "moderate-rain",
                    "stresses": {"rainfall_mm_24h": 20},
                    "physical_cost": 0.2,
                },
                {
                    "scenario_id": "large-rain",
                    "stresses": {
                        "rainfall_mm_24h": 50,
                        "temperature_anomaly_c": 3,
                    },
                    "physical_cost": 0.5,
                },
            ],
            "priority_inputs": {
                "current_anomaly": 0.4,
                "resilience_vulnerability": 0.6,
                "potential_consequence": 0.8,
                "staleness": 0.2,
            },
        }
    )
    assert result["virtual_stress_test"]["state_features"]["water_level_m"] == 2
    assert result["virtual_stress_test"]["resilience_margin"]["critical_scenario_id"] == "large-rain"
    assert result["failure_genome"]["dominant"]["genome"] == "filling_overtopping_erosion"
    assert result["priorities"]["hazard_priority"]["uncertainty_increases_score"] is False


def test_cascade_benchmark_structure_passes_but_evidence_gate_blocks():
    root = Path(__file__).resolve().parent.parent
    validator = root / "scripts/validate_cascade_benchmark.py"
    structure = subprocess.run(
        [sys.executable, str(validator), "--allow-incomplete"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert structure.returncode == 0, structure.stdout + structure.stderr
    assert "EVIDENCE INCOMPLETE" in structure.stdout
    strict = subprocess.run(
        [sys.executable, str(validator)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert strict.returncode == 1
    assert "evidence blocker" in strict.stdout
