"""Read-only evidence-case routes shared across operational product surfaces."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.services.evidence_case_service import resolve_evidence_case

router = APIRouter(prefix="/api/evidence-cases", tags=["evidence-cases"])


@router.get("/{rgi_id}")
def evidence_case(
    rgi_id: str,
    lake_id: str | None = Query(default=None, max_length=160),
    year: int = Query(default=2024, ge=2017, le=2024),
    scope: Literal["local_inventory", "annual_screening", "archive_context", "planning_context"] = Query(
        default="local_inventory"
    ),
) -> dict:
    """Return an exact local evidence package or a glacier-only abstention."""
    return resolve_evidence_case(rgi_id=rgi_id, lake_id=lake_id, year=year, scope=scope)
