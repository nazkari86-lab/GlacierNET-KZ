"""Dashboard aggregates for the web UI."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from app.routers.models import MODELS_CATALOG, list_models
from app.storage.results import get_history
from app.tasks import get_task_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _status_map(db_status: str) -> str:
    mapping = {
        "completed": "completed",
        "processing": "processing",
        "failed": "failed",
        "queued": "queued",
        "pending": "queued",
        "running": "processing",
    }
    return mapping.get(db_status, "completed")


@router.get("/stats")
async def dashboard_stats() -> dict[str, Any]:
    history = get_history(limit=500, offset=0)
    models = list_models()
    task_mgr = get_task_manager()
    task_stats = task_mgr.get_stats()

    total_area = sum(h.get("area_km2") or 0 for h in history)
    model_counts = Counter(h.get("model_name") or "unknown" for h in history)

    segments_by_day: dict[str, int] = Counter()
    for h in history:
        created = h.get("created_at") or ""
        try:
            day = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%a")
        except ValueError:
            day = "Mon"
        segments_by_day[day] += 1

    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    segments_over_time = [{"label": d, "values": [segments_by_day.get(d, 0)]} for d in day_order]

    colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#14b8a6"]
    model_usage = []
    for i, (name, count) in enumerate(model_counts.most_common(6)):
        display = next(
            (m["display_name"] for m in MODELS_CATALOG if m["name"] == name),
            name,
        )
        model_usage.append({"label": display, "value": count, "color": colors[i % len(colors)]})

    if not model_usage and models:
        model_usage = [
            {"label": m["display_name"], "value": 1, "color": colors[i % len(colors)]} for i, m in enumerate(models[:4])
        ]

    recent_tasks = []
    for h in history[:10]:
        created = h.get("created_at") or datetime.now(timezone.utc).isoformat()
        try:
            date_str = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            date_str = created[:10]

        display = next(
            (m["display_name"] for m in MODELS_CATALOG if m["name"] == h.get("model_name")),
            h.get("model_name") or "unknown",
        )
        recent_tasks.append(
            {
                "id": h.get("task_id", ""),
                "model": display,
                "area_km2": h.get("area_km2") or 0,
                "date": date_str,
                "status": _status_map(h.get("status") or "completed"),
            }
        )

    active = task_stats.get("running", 0) + task_stats.get("pending", 0)

    return {
        "total_segments": len(history),
        "total_area_km2": round(total_area, 1),
        "models_registered": len(models),
        "active_tasks": active,
        "segments_over_time": segments_over_time,
        "model_usage": model_usage,
        "recent_tasks": recent_tasks,
    }
