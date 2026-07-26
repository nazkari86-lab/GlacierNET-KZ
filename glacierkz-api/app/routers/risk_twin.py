"""Safety-bounded Active Cryosphere Risk Twin endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.risk_twin.workflow import evaluate_basin_payload

router = APIRouter(prefix="/api/risk-twin", tags=["risk-twin"])


class ObservationInput(BaseModel):
    observation_id: str
    variable: str
    value: float
    uncertainty_std: float = Field(gt=0)
    timestamp: str
    sensor: str
    quality_flags: list[str] = Field(default_factory=list)
    spatial_support: str = "basin_screening"


class ActionInput(BaseModel):
    action_id: str
    label: str
    target_variables: list[str]
    expected_observation_variance: dict[str, float]
    cost: float = Field(default=0, ge=0)
    latency_hours: float = Field(default=0, ge=0)
    available: bool = True


class StressModelInput(BaseModel):
    coefficients: dict[str, float]
    intercept: float
    transition_threshold: float
    state_coefficients: dict[str, float] = Field(default_factory=dict)
    calibrated: bool = False
    calibration_reference: str | None = None
    model_id: str = "linear_stress_screen_v1"
    variable_units: dict[str, str] = Field(default_factory=dict)


class StressScenarioInput(BaseModel):
    scenario_id: str
    stresses: dict[str, float]
    physical_cost: float = Field(ge=0)
    provenance: list[str] = Field(default_factory=list)


class PriorityInput(BaseModel):
    current_anomaly: float = Field(ge=0, le=1)
    resilience_vulnerability: float | None = Field(default=None, ge=0, le=1)
    potential_consequence: float = Field(ge=0, le=1)
    staleness: float = Field(default=0, ge=0, le=1)


class RiskTwinRequest(BaseModel):
    basin_id: str
    observations: list[ObservationInput]
    actions: list[ActionInput] = Field(default_factory=list)
    required_variables: list[str] | None = None
    decision_weights: dict[str, float] | None = None
    missing_variance: float = Field(default=1.0, gt=0)
    cost_weight: float = Field(default=1.0, ge=0)
    latency_cost_per_hour: float = Field(default=0.0, ge=0)
    counterfactual_deltas: dict[str, float] | None = None
    require_probability_calibration: bool = True
    stress_model: StressModelInput | None = None
    stress_scenarios: list[StressScenarioInput] | None = None
    priority_inputs: PriorityInput | None = None


@router.get("/readiness")
def risk_twin_readiness() -> dict[str, Any]:
    return {
        "status": "research_baseline",
        "available": [
            "typed partial observations",
            "scalar Bayesian assimilation",
            "causal cascade graph",
            "model-based value of information",
            "abstention",
            "counterfactual screening",
            "split-conformal scalar intervals",
            "declared ensemble uncertainty propagation",
            "virtual stress surface with explicit model coefficients",
            "Failure Genome screening taxonomy",
            "separate hazard and observation priorities",
        ],
        "blocked": [
            "calibrated event probabilities",
            "Central Asia retrospective event benchmark",
            "field-validated bathymetry/freeboard/dam state",
            "calibrated physical resilience margins",
            "official warning integration",
        ],
        "safety_statement": "screening evidence only; not an official warning",
    }


@router.post("/evaluate")
def evaluate_risk_twin(request: RiskTwinRequest) -> dict[str, Any]:
    payload = (
        request.model_dump(exclude_none=True) if hasattr(request, "model_dump") else request.dict(exclude_none=True)
    )
    try:
        return evaluate_basin_payload(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
