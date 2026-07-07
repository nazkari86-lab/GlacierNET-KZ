"""Expose on-disk data coverage for the web dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services.data_coverage_service import (
    get_data_coverage,
    get_decision_readiness,
    load_csv_table,
    load_glacier_areas,
)

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/coverage", summary="Pipeline data coverage (raw TIFs, predictions, CSV)")
async def data_coverage() -> dict[str, Any]:
    return get_data_coverage()


@router.get("/areas", summary="Glacier area time series from results CSV")
async def glacier_areas(method: str | None = None) -> dict[str, Any]:
    rows = load_glacier_areas()
    if method:
        method_upper = method.upper()
        rows = [r for r in rows if r.get("method", "").upper() == method_upper]
    return {"rows": rows, "count": len(rows)}


@router.get("/decision-readiness", summary="Decision-ready time series, year quality and trend summary")
async def decision_readiness() -> dict[str, Any]:
    return get_decision_readiness()


@router.get("/year-quality", summary="Per-year data quality and confidence scores")
async def year_quality() -> dict[str, Any]:
    rows = load_csv_table("year_quality_scores.csv")
    return {"rows": rows, "count": len(rows)}
