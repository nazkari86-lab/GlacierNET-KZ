"""Endpoints for individual glaciers from the local RGI study-area subset."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.services.glacier_registry_service import (
    get_glacier,
    glacier_report,
    glacier_timeseries,
    list_glaciers,
)

router = APIRouter(prefix="/api/glaciers", tags=["glaciers"])


@router.get("")
def glaciers(
    search: str = Query(""),
    named_only: bool = Query(False),
    min_area_km2: float = Query(0.0, ge=0),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
):
    return list_glaciers(search, named_only, min_area_km2, offset, limit)


@router.get("/{rgi_id}")
def glacier_detail(rgi_id: str):
    return get_glacier(rgi_id, include_geometry=True)


@router.get("/{rgi_id}/timeseries")
def glacier_series(rgi_id: str, method: str = Query("ndsi")):
    return glacier_timeseries(rgi_id, method)


@router.get("/{rgi_id}/report")
def download_glacier_report(rgi_id: str, method: str = Query("ndsi")):
    report = glacier_report(rgi_id, method)
    safe_id = rgi_id.replace("/", "_")
    return Response(
        json.dumps(report, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_id}-{method}-report.json"'},
    )
