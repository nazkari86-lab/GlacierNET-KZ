"""Validated CryoGenesis discovery routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import cryogenesis_service

router = APIRouter(prefix="/api/cryogenesis", tags=["cryogenesis"])


@router.get("/status")
def status() -> dict:
    return cryogenesis_service.discovery_status()


@router.get("/cohorts")
def cohorts() -> dict:
    return cryogenesis_service.list_cohorts()


@router.get("/glaciers/{rgi_id}/passport")
def passport(rgi_id: str, cohort_id: str | None = None) -> dict:
    try:
        return cryogenesis_service.get_passport(rgi_id, cohort_id)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=404,
            detail=("No exact validated CryoGenesis passport exists for this glacier and cohort"),
        ) from error


@router.get("/discoveries")
def discoveries(
    cohort_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return cryogenesis_service.list_discoveries(
        cohort_id=cohort_id,
        status=status,
        limit=limit,
    )
