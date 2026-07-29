"""Canonical, fail-closed packages for one glacier evidence case.

An evidence case may describe a glacier alone or one explicitly identified lake
from that glacier's already selected local context.  It never infers a
lake-glacier relationship from proximity, names, or a nearest-neighbour match.
"""

from __future__ import annotations

from typing import Any, Literal

from app.services.risk_twin_context_service import risk_twin_context

EvidenceSourceScope = Literal[
    "local_inventory",
    "annual_screening",
    "archive_context",
    "planning_context",
]

EVIDENCE_SOURCE_SCOPES: set[str] = {
    "local_inventory",
    "annual_screening",
    "archive_context",
    "planning_context",
}


def _exact_lake_feature(context: dict[str, Any], lake_id: str) -> dict[str, Any] | None:
    """Return only an exact identifier match from the supplied spatial context."""
    # ``tien_shan_lakes`` is tied to the explicit inventory year in the
    # context query.  Keep the inventory layer second so an exact current
    # local lake match always wins over a broader reference inventory match.
    for layer_name in ("tien_shan_lakes", "hma_gli_2015_2018"):
        features = context.get("layers", {}).get(layer_name, {}).get("features", [])
        for feature in features:
            candidate_id = feature.get("properties", {}).get("lake_id")
            if isinstance(candidate_id, str) and candidate_id == lake_id:
                return {"layer": layer_name, **feature}
    return None


def _glacier_facts(glacier: dict[str, Any]) -> dict[str, Any]:
    """Keep a stable, useful subset of the registry record in each package."""
    return {key: glacier.get(key) for key in ("rgi_id", "name", "rgi_area_km2", "geometry") if key in glacier}


def resolve_evidence_case(
    rgi_id: str,
    lake_id: str | None = None,
    year: int = 2024,
    lake_inventory_year: int = 2023,
    scope: EvidenceSourceScope = "local_inventory",
) -> dict[str, Any]:
    """Resolve an auditable local case without fabricating a lake association."""
    if scope not in EVIDENCE_SOURCE_SCOPES:
        raise ValueError(f"Unknown evidence source scope: {scope}")

    context = risk_twin_context(rgi_id, year=year, lake_inventory_year=lake_inventory_year)
    glacier = context["glacier"]
    claim_limits = context.get("interpretation", {}).get("not_allowed", [])
    package: dict[str, Any] = {
        "schema": "glaciernet-kz.evidence-case.v1",
        "case": {
            "rgi_id": glacier["rgi_id"],
            "lake_id": None,
            "year": year,
            "lake_inventory_year": lake_inventory_year,
            "source_scope": scope,
        },
        "facts": {"glacier": _glacier_facts(glacier), "lake": None},
        "claim_limits": claim_limits,
        "sources": context.get("sources", []),
        "next_actions": [
            "Inspect the cited local source layers and imagery before making a field or operational decision."
        ],
    }
    if lake_id is None:
        return {
            **package,
            "resolution": "glacier_context_only",
            "reason": "No lake ID was supplied; returning the verified local glacier context only.",
        }

    lake_feature = _exact_lake_feature(context, lake_id)
    if lake_feature is None:
        return {
            **package,
            "resolution": "glacier_context_only",
            "reason": f"Lake ID {lake_id!r} was not found in the local context for this RGI glacier.",
            "next_actions": [
                "Inspect the local lake inventory and source imagery before linking a lake case to this glacier.",
            ],
        }

    package["case"]["lake_id"] = lake_id
    package["facts"]["lake"] = lake_feature
    return {
        **package,
        "resolution": "local_case",
        "reason": "The requested lake ID exactly matches a feature in the selected local context; this is not a validated physical lake-to-glacier linkage.",
    }
