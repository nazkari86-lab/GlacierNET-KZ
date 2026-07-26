"""Human-readable, safety-bounded daily decision brief."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_daily_decision_brief(
    basin_assessments: list[dict[str, Any]],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    timestamp = generated_at or datetime.now(timezone.utc)
    attention = [item for item in basin_assessments if item.get("decision_support", {}).get("abstain")]
    changed = [item for item in basin_assessments if item.get("significant_changes")]
    ranked = sorted(
        basin_assessments,
        key=lambda item: (
            item.get("decision_support", {}).get("abstain") is False,
            -float(item.get("attention_score", 0)),
            str(item.get("basin_id", "")),
        ),
    )
    priority = ranked[0] if ranked else None
    return {
        "generated_at": timestamp.astimezone(timezone.utc).isoformat(),
        "brief_type": "screening_decision_support",
        "summary": {
            "basins_analysed": len(basin_assessments),
            "significant_changes": len(changed),
            "high_uncertainty": len(attention),
        },
        "priority": priority,
        "safety_statement": (
            "Screening evidence only. This brief is not an official warning and does not confirm an imminent GLOF."
        ),
    }
