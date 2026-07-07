"""Pipeline run tracking — minimal in-memory store for the web UI."""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

STAGE_NAMES = ["ingest", "preprocess", "train", "evaluate", "deploy"]

_runs: dict[str, dict[str, Any]] = {}


def _build_stages(run: dict[str, Any]) -> list[dict[str, Any]]:
    progress_epoch = run.get("progress", 0)
    total = len(STAGE_NAMES)
    active_idx = min(progress_epoch // 20, total - 1) if run["status"] == "running" else -1

    stages: list[dict[str, Any]] = []
    for i, name in enumerate(STAGE_NAMES):
        if run["status"] == "success":
            st, prog = "success", 100
        elif run["status"] == "failed" and i == active_idx:
            st, prog = "failed", run.get("stage_progress", 50)
        elif run["status"] == "cancelled":
            st = "skipped" if i > active_idx else ("running" if i == active_idx else "success")
            prog = 100 if st == "success" else (run.get("stage_progress", 30) if st == "running" else 0)
        elif run["status"] == "running":
            if i < active_idx:
                st, prog = "success", 100
            elif i == active_idx:
                st, prog = "running", run.get("stage_progress", 45)
            else:
                st, prog = "pending", 0
        elif run["status"] == "pending":
            st, prog = ("waiting", 0) if i == 0 else ("pending", 0)
        else:
            st, prog = "pending", 0

        stages.append(
            {
                "id": f"{run['id']}-{name}",
                "name": name,
                "status": st,
                "progress": prog,
            }
        )
    return stages


def _run_to_response(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": run["id"],
        "name": run["name"],
        "status": run["status"],
        "stages": _build_stages(run),
        "createdAt": run["created_at"],
        "triggeredBy": run.get("triggered_by", "system"),
        "branch": run.get("branch", "main"),
        "commit": run.get("commit"),
    }


def _advance_runs() -> None:
    now = time.time()
    for run in _runs.values():
        if run["status"] != "running":
            continue
        elapsed = now - run.get("started_at", now)
        run["progress"] = min(int(elapsed * 5), 100)
        run["stage_progress"] = int((elapsed * 15) % 100)
        if run["progress"] >= 100:
            run["status"] = "success"
            run["finished_at"] = now


def _seed_runs() -> None:
    if _runs:
        return
    now = time.time()
    samples = [
        {
            "id": "run-001",
            "name": "Zailiysky segmentation pipeline",
            "status": "success",
            "created_at": (now - 86400),
            "triggered_by": "scheduler",
            "branch": "main",
            "commit": "a1b2c3d4e5f67890",
            "progress": 100,
            "stage_progress": 100,
        },
        {
            "id": "run-002",
            "name": "Tuyuksu model retrain",
            "status": "running",
            "created_at": (now - 3600),
            "started_at": now - 120,
            "triggered_by": "admin",
            "branch": "feature/unet-v2",
            "commit": "deadbeef12345678",
            "progress": 35,
            "stage_progress": 62,
        },
        {
            "id": "run-003",
            "name": "Kumtor dataset ingest",
            "status": "failed",
            "created_at": (now - 7200),
            "triggered_by": "operator",
            "branch": "main",
            "progress": 20,
            "stage_progress": 50,
        },
    ]
    for s in samples:
        _runs[s["id"]] = s


_seed_runs()


@router.get("/runs")
async def list_runs(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> dict[str, Any]:
    _advance_runs()
    runs = sorted(_runs.values(), key=lambda r: r["created_at"], reverse=True)

    if q:
        ql = q.lower()
        runs = [r for r in runs if ql in r["name"].lower()]
    if status and status != "all":
        runs = [r for r in runs if r["status"] == status]

    return {"runs": [_run_to_response(r) for r in runs], "total": len(runs)}


@router.post("/runs/{run_id}/rerun")
async def rerun_run(run_id: str) -> dict[str, Any]:
    old = _runs.get(run_id)
    if old is None:
        raise HTTPException(404, f"Pipeline run {run_id!r} not found")

    new_id = f"run-{uuid.uuid4().hex[:8]}"
    now = time.time()
    run = {
        "id": new_id,
        "name": old["name"],
        "status": "running",
        "created_at": now,
        "started_at": now,
        "triggered_by": old.get("triggered_by", "system"),
        "branch": old.get("branch", "main"),
        "commit": old.get("commit"),
        "progress": 0,
        "stage_progress": 5,
    }
    _runs[new_id] = run
    return _run_to_response(run)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, Any]:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"Pipeline run {run_id!r} not found")
    if run["status"] in ("success", "failed", "cancelled"):
        raise HTTPException(409, f"Run already terminal: {run['status']}")
    run["status"] = "cancelled"
    run["finished_at"] = time.time()
    return _run_to_response(run)
