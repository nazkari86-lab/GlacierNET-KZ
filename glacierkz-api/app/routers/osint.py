"""OSINT Event Radar API with explicit claim boundaries."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query

from app.services.glacier_registry_service import get_glacier
from app.services.osint_service import build_event_radar, enrich_and_rank, osint_readiness, source_catalog

router = APIRouter(prefix="/api/osint", tags=["osint"])


@router.get("/events")
def events(
    rgi_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    source_tier: str | None = Query(default=None),
    scope: Literal["all", "near_glacier", "regional_trigger_context", "broad_context", "unresolved"] = "all",
    limit: int = Query(default=100, ge=1, le=500),
    refresh: bool = Query(default=False),
) -> dict[str, Any]:
    snapshot = build_event_radar(force_refresh=refresh)
    filtered = snapshot["events"]
    if rgi_id:
        # Re-link every retained regional signal to the explicitly selected
        # glacier. This answers "what is relevant to this object?" instead of
        # silently returning only events for which it happened to be nearest.
        target = get_glacier(rgi_id, include_geometry=False)
        filtered = enrich_and_rank(filtered, [target])
    if event_type:
        filtered = [item for item in filtered if item["event_type"] == event_type]
    if source_tier:
        filtered = [item for item in filtered if item["source_tier"] == source_tier]
    if scope != "all":
        filtered = [item for item in filtered if item["link_scope"] == scope]
    return {
        **snapshot,
        "events": filtered[:limit],
        "query": {
            "rgi_id": rgi_id,
            "event_type": event_type,
            "source_tier": source_tier,
            "scope": scope,
            "limit": limit,
        },
        "returned": min(limit, len(filtered)),
        "matched": len(filtered),
    }


@router.get("/sources")
def sources() -> dict[str, Any]:
    return source_catalog()


@router.get("/readiness")
def readiness() -> dict[str, Any]:
    return osint_readiness()
