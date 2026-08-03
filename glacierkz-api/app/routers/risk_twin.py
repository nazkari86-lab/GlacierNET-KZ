"""Safety-bounded Active Cryosphere Risk Twin endpoints."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.rbac import User, get_current_user, user_has_scope
from app.services.ml_workspace_service import analyze_glacier, find_ml_case
from app.services.risk_twin_context_service import regional_lake_screening, risk_twin_context
from app.services.risk_twin_integration_service import build_integrated_case
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


class IntegratedCaseRequest(BaseModel):
    year: int = Field(default=2024, ge=2017, le=2024)
    lake_inventory_year: int = 2023
    lake_id: str | None = None
    buffer_km: float = Field(default=10.0, gt=0, le=30)
    run_ml_if_missing: bool = False
    model_name: str = "temporal_s2_terrain_s1"
    use_tta: bool = True
    context_m: int = Field(default=400, ge=0, le=2000)


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
            "calibrated OSINT-to-event likelihood",
        ],
        "safety_statement": "screening evidence only; not an official warning",
        "event_radar": {
            "available": True,
            "endpoint": "/api/osint/events",
            "role": "source-backed acquisition prioritization; never a physical hazard probability",
        },
    }


@router.get("/context/{rgi_id}")
def risk_twin_spatial_context(
    rgi_id: str,
    year: int = 2024,
    lake_inventory_year: int = Query(default=2023),
    buffer_km: float = Query(default=10.0, gt=0, le=30),
) -> dict[str, Any]:
    """Return local lake/event/terrain/SAR context around one RGI glacier.

    The response is intentionally descriptive: geographical proximity is never
    converted into a hazard probability or a claimed lake-glacier connection.
    """
    return risk_twin_context(
        rgi_id,
        year=year,
        buffer_km=buffer_km,
        lake_inventory_year=lake_inventory_year,
    )


@router.get("/regional-scan")
def regional_scan(
    inventory_year: int = Query(default=2023),
    buffer_km: float = Query(default=10.0, gt=0, le=30),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Automatic all-local-inventory observation screening, never a hazard map."""
    payload = regional_lake_screening(inventory_year=inventory_year, buffer_km=buffer_km)
    return {**payload, "candidates": payload["candidates"][:limit], "returned": min(limit, len(payload["candidates"]))}


@router.post("/integrated-case/{rgi_id}")
async def integrated_case(
    rgi_id: str,
    request: IntegratedCaseRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return one ML -> lake -> route -> operator evidence chain.

    Inference is opt-in because it can be expensive.  Missing model/data never
    prevents the GIS context from loading and is reported as an explicit gate.
    """
    ml_case = find_ml_case(rgi_id, year=request.year, model_name=request.model_name)
    ml_reason: str | None = None
    if ml_case is None and request.run_ml_if_missing:
        if not user_has_scope(user, "predict"):
            raise HTTPException(status_code=403, detail="Scope 'predict' required to run ML inference")
        try:
            ml_case = await asyncio.to_thread(
                analyze_glacier,
                rgi_id,
                year=request.year,
                model_name=request.model_name,
                use_tta=request.use_tta,
                context_m=request.context_m,
                refresh=False,
            )
            ml_case["evidence_origin"] = "runtime_local"
        except HTTPException as error:
            ml_reason = str(error.detail)
    return await asyncio.to_thread(
        build_integrated_case,
        rgi_id,
        year=request.year,
        lake_inventory_year=request.lake_inventory_year,
        buffer_km=request.buffer_km,
        lake_id=request.lake_id,
        ml_case=ml_case,
        ml_status_reason=ml_reason,
    )


@router.post("/evaluate")
def evaluate_risk_twin(request: RiskTwinRequest) -> dict[str, Any]:
    payload = (
        request.model_dump(exclude_none=True) if hasattr(request, "model_dump") else request.dict(exclude_none=True)
    )
    try:
        return evaluate_basin_payload(payload)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
