"""Cryosphere Operations API: observations, inspections, evidence, and decisions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.auth.rbac import User, get_current_user, user_has_scope
from app.storage.operations import (
    database,
    insert_record,
    list_rows,
    new_id,
    overview,
    row_by_id,
    seed_demo,
    update_task,
    utc_now,
    verify_audit_chain,
)
from src.operations import assess_domain_shift, next_best_observation

router = APIRouter(prefix="/api/operations", tags=["operations"])
REPO_ROOT = Path(__file__).resolve().parents[3]


def operations_writer(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user_has_scope(user, "write"):
        raise HTTPException(status_code=403, detail="Scope 'write' required")
    return user


Writer = Annotated[User, Depends(operations_writer)]


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class BasinCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    region: str = Field(min_length=2, max_length=240)
    status: Literal["shadow_mode", "active", "archived"] = "shadow_mode"
    evidence_tier: Literal["operational_unverified", "customer_verified", "synthetic_demo"] = "operational_unverified"


class AssetCreate(BaseModel):
    basin_id: str
    asset_type: Literal["glacier", "moraine_lake", "sensor", "slope", "infrastructure"]
    name: str = Field(min_length=2, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    status: str = "monitoring"
    evidence_tier: Literal["operational_unverified", "customer_verified", "synthetic_demo"] = "operational_unverified"
    model_version: str | None = None
    data_version: str | None = None
    allowed_use: str = "screening and evidence management with human review"
    forbidden_use: str = "official warning or autonomous emergency action"


class ObservationCreate(BaseModel):
    asset_id: str
    observation_type: str = Field(min_length=2, max_length=120)
    observed_at: str
    source: str = Field(min_length=2, max_length=240)
    values: dict[str, Any] = Field(default_factory=dict)
    quality_status: Literal["usable", "review_required", "poor_quality", "incompatible"] = "review_required"
    uncertainty: float = Field(ge=0, le=1)
    artifact_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class DomainShiftRequest(BaseModel):
    out_of_distribution_score: float = Field(ge=0, le=1)
    model_disagreement: float = Field(ge=0, le=1)
    preprocessing_compatible: bool
    region_in_validation_scope: bool


class CandidateCreate(DomainShiftRequest):
    asset_id: str
    observation_id: str | None = None
    change_type: str = Field(min_length=2, max_length=120)
    magnitude: float
    uncertainty: float = Field(ge=0, le=1)
    staleness: float = Field(ge=0, le=1)
    data_quality_gap: float = Field(ge=0, le=1)
    expected_information_gain: float = Field(ge=0, le=1)
    evidence_tier: Literal["operational_unverified", "customer_verified", "synthetic_demo"] = "operational_unverified"
    detected_at: str


class InspectionTaskCreate(BaseModel):
    asset_id: str
    candidate_id: str | None = None
    action_type: str
    priority_score: float = Field(ge=0, le=1)
    rationale: str
    assigned_to: str | None = None
    due_at: str | None = None


class TaskUpdate(BaseModel):
    status: Literal["queued", "assigned", "in_progress", "completed", "cancelled"]
    assigned_to: str | None = None


class FieldReportCreate(BaseModel):
    task_id: str
    asset_id: str
    observer: str = Field(min_length=2, max_length=160)
    observed_at: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    measurements: dict[str, Any] = Field(default_factory=dict)
    checklist: dict[str, bool | str | None] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=10_000)
    attachment_manifest: list[dict[str, Any]] = Field(default_factory=list)
    signature: str = Field(min_length=2, max_length=240)
    sync_status: Literal["offline_draft", "synced"] = "synced"


class EvidenceCaseCreate(BaseModel):
    asset_id: str
    title: str = Field(min_length=2, max_length=200)
    status: Literal["open", "under_review", "decision_recorded", "closed"] = "open"
    summary: str = Field(min_length=2, max_length=20_000)
    limitations: str = Field(min_length=2, max_length=10_000)
    allowed_use: str = "operational screening with human review"
    forbidden_use: str = "official warning or autonomous emergency action"
    reviewer: str | None = None


class DecisionCreate(BaseModel):
    evidence_case_id: str
    decision: str = Field(min_length=2, max_length=500)
    rationale: str = Field(min_length=2, max_length=10_000)
    decided_by: str = Field(min_length=2, max_length=160)
    decided_at: str
    outcome: str | None = Field(default=None, max_length=10_000)
    status: Literal["provisional", "approved", "superseded"] = "provisional"


@router.get("/readiness")
def readiness() -> dict[str, Any]:
    return {
        "status": "operations_mvp",
        "available": [
            "operations registry",
            "observation inbox",
            "change-candidate queue",
            "Next Best Observation",
            "domain-shift abstention",
            "field reports",
            "evidence cases",
            "human decision records",
            "SHA-256 audit chain",
            "JSON evidence export",
        ],
        "blocked": [
            "official warning integration",
            "calibrated GLOF probability",
            "automatic emergency action",
            "production sensor connectors",
            "partner identity and SSO configuration",
        ],
        "safety_statement": "The MVP supports shadow-mode operations, not official warnings.",
    }


@router.get("/overview")
def operations_overview() -> dict[str, Any]:
    with database() as connection:
        return overview(connection)


@router.get("/demo")
def demo_overview() -> dict[str, Any]:
    with database(Path(":memory:")) as connection:
        result = seed_demo(connection)
        result["demo_only"] = True
        result["persistence"] = "none"
        return result


@router.get("/assets")
def assets(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    with database() as connection:
        rows = list_rows(connection, "assets", limit=limit)
    return {"items": rows, "total": len(rows)}


@router.get("/audit")
def audit(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
    with database() as connection:
        return {
            "chain": verify_audit_chain(connection),
            "events": list_rows(connection, "audit_events", limit=limit),
        }


@router.post("/domain-shift")
def domain_shift(request: DomainShiftRequest) -> dict[str, Any]:
    return assess_domain_shift(**_dump(request))


@router.get("/domain-shift/current-model")
def current_model_domain_shift() -> dict[str, Any]:
    report_path = REPO_ROOT / "benchmarks/v2/provisional/zhetysu_candidate_rgi_2024_summary.json"
    if not report_path.is_file():
        raise HTTPException(status_code=503, detail="External stress evidence unavailable")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = report["metrics_bootstrap"]
    return {
        "model_scope": "Ile Alatau one-AOI silver benchmark",
        "external_stress_geography": "broad provisional Zhetysu candidate filter",
        "hard_dice": metrics["hard_dice"],
        "area_error_percent": metrics["area_error_percent"],
        "status": "abstain_local_validation_required",
        "allowed_use": "data-quality triage and local calibration planning",
        "forbidden_use": ("external-region accuracy claim, event probability, or official warning"),
        "evidence_path": str(report_path.relative_to(REPO_ROOT)),
    }


@router.post("/basins", status_code=201)
def create_basin(request: BasinCreate, user: Writer) -> dict[str, Any]:
    now = utc_now()
    record = {"id": new_id("basin"), **_dump(request), "created_at": now}
    with database() as connection:
        return insert_record(connection, "basins", record, actor=user.user_id)


@router.post("/assets", status_code=201)
def create_asset(request: AssetCreate, user: Writer) -> dict[str, Any]:
    now = utc_now()
    record = {
        "id": new_id("asset"),
        **_dump(request),
        "created_at": now,
        "updated_at": now,
    }
    with database() as connection:
        if not row_by_id(connection, "basins", request.basin_id):
            raise HTTPException(status_code=404, detail="Basin not found")
        return insert_record(connection, "assets", record, actor=user.user_id)


@router.post("/observations", status_code=201)
def create_observation(request: ObservationCreate, user: Writer) -> dict[str, Any]:
    payload = _dump(request)
    values = payload.pop("values")
    record = {
        "id": new_id("obs"),
        **payload,
        "values_json": _json(values),
        "created_by": user.user_id,
        "created_at": utc_now(),
    }
    with database() as connection:
        if not row_by_id(connection, "assets", request.asset_id):
            raise HTTPException(status_code=404, detail="Asset not found")
        return insert_record(connection, "observations", record, actor=user.user_id)


@router.post("/change-candidates", status_code=201)
def create_change_candidate(request: CandidateCreate, user: Writer) -> dict[str, Any]:
    domain = assess_domain_shift(
        out_of_distribution_score=request.out_of_distribution_score,
        model_disagreement=request.model_disagreement,
        preprocessing_compatible=request.preprocessing_compatible,
        region_in_validation_scope=request.region_in_validation_scope,
    )
    recommendation = next_best_observation(
        uncertainty=request.uncertainty,
        staleness=request.staleness,
        data_quality_gap=request.data_quality_gap,
        model_disagreement=request.model_disagreement,
        expected_information_gain=request.expected_information_gain,
        domain_shift_status=str(domain["status"]),
    )
    record = {
        "id": new_id("candidate"),
        "asset_id": request.asset_id,
        "observation_id": request.observation_id,
        "change_type": request.change_type,
        "magnitude": request.magnitude,
        "uncertainty": request.uncertainty,
        "data_quality_gap": request.data_quality_gap,
        "model_disagreement": request.model_disagreement,
        "expected_information_gain": request.expected_information_gain,
        "domain_shift_status": domain["status"],
        "priority_score": recommendation["score"],
        "next_action": recommendation["action"],
        "rationale": recommendation["reason"],
        "status": "requires_review",
        "evidence_tier": request.evidence_tier,
        "detected_at": request.detected_at,
        "created_at": utc_now(),
    }
    with database() as connection:
        if not row_by_id(connection, "assets", request.asset_id):
            raise HTTPException(status_code=404, detail="Asset not found")
        result = insert_record(
            connection,
            "change_candidates",
            record,
            actor=user.user_id,
        )
    result["domain_shift"] = domain
    result["next_best_observation"] = recommendation
    return result


@router.post("/inspection-tasks", status_code=201)
def create_inspection_task(request: InspectionTaskCreate, user: Writer) -> dict[str, Any]:
    now = utc_now()
    record = {
        "id": new_id("task"),
        **_dump(request),
        "status": "queued",
        "offline_package_status": "not_built",
        "created_at": now,
        "updated_at": now,
    }
    with database() as connection:
        if not row_by_id(connection, "assets", request.asset_id):
            raise HTTPException(status_code=404, detail="Asset not found")
        return insert_record(connection, "inspection_tasks", record, actor=user.user_id)


@router.patch("/inspection-tasks/{task_id}")
def patch_inspection_task(
    task_id: str,
    request: TaskUpdate,
    user: Writer,
) -> dict[str, Any]:
    with database() as connection:
        record = update_task(
            connection,
            task_id,
            status=request.status,
            assigned_to=request.assigned_to,
            actor=user.user_id,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Inspection task not found")
        return record


@router.post("/field-reports", status_code=201)
def create_field_report(request: FieldReportCreate, user: Writer) -> dict[str, Any]:
    payload = _dump(request)
    record = {
        "id": new_id("field"),
        "task_id": payload["task_id"],
        "asset_id": payload["asset_id"],
        "observer": payload["observer"],
        "observed_at": payload["observed_at"],
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "measurements_json": _json(payload["measurements"]),
        "checklist_json": _json(payload["checklist"]),
        "notes": payload["notes"],
        "attachment_manifest_json": _json(payload["attachment_manifest"]),
        "signature": payload["signature"],
        "sync_status": payload["sync_status"],
        "created_at": utc_now(),
    }
    with database() as connection:
        if not row_by_id(connection, "inspection_tasks", request.task_id):
            raise HTTPException(status_code=404, detail="Inspection task not found")
        result = insert_record(connection, "field_reports", record, actor=user.user_id)
        if request.sync_status == "synced":
            update_task(
                connection,
                request.task_id,
                status="completed",
                assigned_to=request.observer,
                actor=user.user_id,
            )
        return result


@router.post("/evidence-cases", status_code=201)
def create_evidence_case(request: EvidenceCaseCreate, user: Writer) -> dict[str, Any]:
    now = utc_now()
    record = {
        "id": new_id("case"),
        **_dump(request),
        "created_at": now,
        "updated_at": now,
    }
    with database() as connection:
        if not row_by_id(connection, "assets", request.asset_id):
            raise HTTPException(status_code=404, detail="Asset not found")
        return insert_record(connection, "evidence_cases", record, actor=user.user_id)


@router.post("/decisions", status_code=201)
def create_decision(request: DecisionCreate, user: Writer) -> dict[str, Any]:
    record = {"id": new_id("decision"), **_dump(request), "created_at": utc_now()}
    with database() as connection:
        if not row_by_id(connection, "evidence_cases", request.evidence_case_id):
            raise HTTPException(status_code=404, detail="Evidence case not found")
        return insert_record(connection, "decisions", record, actor=user.user_id)


@router.get("/evidence-cases/{case_id}/export")
def export_evidence_case(case_id: str) -> Response:
    with database() as connection:
        evidence_case = row_by_id(connection, "evidence_cases", case_id)
        if not evidence_case:
            raise HTTPException(status_code=404, detail="Evidence case not found")
        asset = row_by_id(connection, "assets", evidence_case["asset_id"])
        related: dict[str, list[dict[str, Any]]] = {}
        for table in (
            "observations",
            "change_candidates",
            "inspection_tasks",
            "field_reports",
        ):
            # Safe dynamic identifier: table comes only from the fixed tuple above.
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE asset_id = ? ORDER BY created_at",  # nosec B608
                (evidence_case["asset_id"],),
            ).fetchall()
            related[table] = [dict(row) for row in rows]
        decisions = connection.execute(
            "SELECT * FROM decisions WHERE evidence_case_id = ? ORDER BY decided_at",
            (case_id,),
        ).fetchall()
        audit_chain = verify_audit_chain(connection)
        bundle = {
            "schema": "glaciernet-kz.operations-evidence-case.v1",
            "generated_at": utc_now(),
            "case": evidence_case,
            "asset": asset,
            "related": related,
            "decisions": [dict(row) for row in decisions],
            "audit_chain": audit_chain,
            "allowed_use": evidence_case["allowed_use"],
            "forbidden_use": evidence_case["forbidden_use"],
            "safety_statement": (
                "This evidence bundle documents a human-reviewed workflow; it is not an official warning."
            ),
        }
    canonical = _json(bundle)
    bundle["bundle_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    content = json.dumps(bundle, indent=2, ensure_ascii=False)
    filename = f"{case_id}-evidence.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Artifact-SHA256": bundle["bundle_sha256"],
        },
    )
