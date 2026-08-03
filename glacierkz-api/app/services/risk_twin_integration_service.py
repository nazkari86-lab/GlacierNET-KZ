"""Join glacier ML evidence to the spatial Risk Twin without creating hazard claims."""

from __future__ import annotations

from typing import Any

from app.services.ml_workspace_service import find_ml_case
from app.services.risk_twin_context_service import risk_twin_context


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def ml_evidence_gate(case: dict[str, Any] | None) -> dict[str, Any]:
    """Decide whether one ML boundary can support screening or needs review."""
    if not case:
        return {
            "status": "not_available",
            "usable_for_boundary_screening": False,
            "usable_for_temporal_change": False,
            "reasons": ["No glacier-specific ML evidence case is available for the selected year."],
        }
    metrics = case.get("metrics", {})
    overlap = _finite(metrics.get("rgi_overlap_iou"))
    uncertainty = _finite(metrics.get("uncertain_fraction_in_review_zone"))
    predicted_area = _finite(metrics.get("predicted_area_km2"))
    reasons: list[str] = []
    if predicted_area is None or predicted_area <= 0:
        reasons.append("The selected ML component is empty or has no measurable area.")
    if overlap is None or overlap < 0.35:
        reasons.append("Raw ML-to-RGI overlap is below the 0.35 screening gate.")
    if uncertainty is None or uncertainty > 0.25:
        reasons.append("More than 25% of the review zone is predictively uncertain.")
    passed = not reasons
    return {
        "status": "screening_ready" if passed else "expert_review_required",
        "usable_for_boundary_screening": passed,
        # One current boundary versus an old inventory is not a temporal trend.
        "usable_for_temporal_change": False,
        "rgi_overlap_iou": overlap,
        "uncertain_fraction_in_review_zone": uncertainty,
        "reasons": reasons or ["The boundary passes the declared local screening gates."],
        "claim_boundary": (
            "ML can support boundary screening after review; it still cannot support an event probability."
            if passed
            else "ML changes the next evidence task to boundary review; its area delta is blocked from trend or hazard use."
        ),
    }


def integrated_case_decision(candidate: dict[str, Any] | None, ml_case: dict[str, Any] | None) -> dict[str, Any]:
    """Build one explainable workflow priority; never a physical-risk score."""
    gate = ml_evidence_gate(ml_case)
    lake_priority = int(round(_finite((candidate or {}).get("observation_priority_0_100")) or 0))
    ml_priority = int(round(_finite((ml_case or {}).get("metrics", {}).get("review_priority_0_100")) or 0))
    case_priority = max(lake_priority, ml_priority)
    if not ml_case:
        driver = "missing_ml_evidence"
        title = "Run glacier-specific ML screening"
        action = "Generate probability, entropy and boundary layers for the linked glacier before interpreting current ice geometry."
    elif gate["status"] == "expert_review_required":
        driver = "ml_boundary_review"
        title = "Review the ML glacier boundary first"
        action = "Inspect the raw and inventory-guided boundaries at full resolution; do not use the area delta until the disagreement is resolved."
    elif candidate and (candidate.get("area_change_percent") is None or lake_priority >= ml_priority):
        driver = "lake_boundary_review"
        title = "Verify the lake contour next"
        action = "Acquire a clear scene and confirm the inventory lake boundary before escalating to field inspection."
    else:
        driver = "route_linkage_review"
        title = "Verify the hydrological linkage"
        action = "Compare the HydroRIVERS planning route with the operator engineering scheme and local hydraulics."
    return {
        "workflow_priority_0_100": case_priority,
        "priority_formula": "max(lake_observation_priority, ml_boundary_review_priority)",
        "lake_observation_priority_0_100": lake_priority,
        "ml_boundary_review_priority_0_100": ml_priority if ml_case else None,
        "driver": driver,
        "title": title,
        "next_action": action,
        "ml_changed_next_action": bool(ml_case and ml_priority > lake_priority),
        "meaning": "Priority of the next evidence task, not hazard, failure, flood or impact probability.",
        "gate": gate,
    }


def build_integrated_case(
    rgi_id: str,
    *,
    year: int,
    lake_inventory_year: int,
    buffer_km: float,
    lake_id: str | None = None,
    ml_case: dict[str, Any] | None = None,
    ml_status_reason: str | None = None,
) -> dict[str, Any]:
    context = risk_twin_context(
        rgi_id,
        year=year,
        buffer_km=buffer_km,
        lake_inventory_year=lake_inventory_year,
    )
    candidates = context.get("screening_candidates", [])
    selected = next((item for item in candidates if lake_id and item.get("lake_id") == lake_id), None)
    if selected is None and candidates:
        selected = candidates[0]
    if ml_case is None:
        ml_case = find_ml_case(rgi_id, year=year)
    decision = integrated_case_decision(selected, ml_case)
    return {
        "schema": "glaciernet-kz.integrated-risk-twin-case.v1",
        "query": {
            "rgi_id": rgi_id,
            "year": year,
            "lake_inventory_year": lake_inventory_year,
            "lake_id": lake_id,
        },
        "context": context,
        "selected_candidate": selected,
        "ml_evidence": ml_case,
        "ml_status_reason": ml_status_reason,
        "decision": decision,
        "evidence_route": [
            {"step": "satellite", "status": "available" if ml_case else "not_analyzed"},
            {"step": "ml_boundary", "status": decision["gate"]["status"]},
            {"step": "lake_inventory", "status": "available" if selected else "not_available"},
            {"step": "downstream_route", "status": context.get("downstream_route", {}).get("status", "not_available")},
            {"step": "operator_action", "status": "screening_only"},
        ],
        "claims_allowed": [
            "workflow priority and next evidence action",
            "glacier-specific ML boundary disagreement and predictive entropy",
            "source-backed spatial planning context",
        ],
        "claims_not_allowed": [
            "GLOF or infrastructure failure probability",
            "flood extent, affected population or expected damage",
            "temporal glacier-loss claim from one ML boundary versus RGI",
        ],
    }
