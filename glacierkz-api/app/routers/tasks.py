# -*- coding: utf-8 -*-
r"""Task management routes for background job orchestration.

Provides CRUD operations for background tasks such as training runs, data
processing jobs, and inference requests.  Tasks follow a simple state
machine::

    pending  ->  running  ->  completed
                          \-> failed
                          \-> cancelled
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    """Payload for creating a new task."""

    name: str = Field(..., min_length=1, max_length=200, description="Human-readable task name")
    description: str = Field("", max_length=2000, description="Optional description")
    priority: int = Field(0, ge=0, le=10, description="Priority (0 = lowest, 10 = highest)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary key/value pairs")


class TaskResponse(BaseModel):
    """Serialised task representation returned to clients."""

    id: str
    name: str
    status: str
    progress: float
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    tasks: list[TaskResponse]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# In-memory store – replace with a real DB / Redis in production.
# ---------------------------------------------------------------------------
_tasks: dict[str, dict[str, Any]] = {}

# Terminal states – a task in one of these cannot be cancelled.
_TERMINAL_STATES: frozenset[str] = frozenset({"completed", "failed", "cancelled"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_to_response(task: dict[str, Any]) -> TaskResponse:
    """Convert an internal task dict to a TaskResponse."""
    return TaskResponse(
        id=task["id"],
        name=task["name"],
        status=task["status"],
        progress=task.get("progress", 0.0),
        result=task.get("result"),
        error=task.get("error"),
    )


def _get_task_or_404(task_id: str) -> dict[str, Any]:
    """Look up a task by ID or raise HTTP 404."""
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id!r} not found",
        )
    return task


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/create",
    response_model=TaskResponse,
    status_code=201,
    summary="Create a new background task",
)
async def create_task(body: TaskCreate) -> TaskResponse:
    """Create a new background task.

    The task starts in *pending* state and transitions to *running* once a
    worker picks it up.

    Returns the newly created task with a unique identifier.
    """
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    now = time.time()

    task: dict[str, Any] = {
        "id": task_id,
        "name": body.name,
        "description": body.description,
        "priority": body.priority,
        "metadata": body.metadata,
        "status": "pending",
        "progress": 0.0,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    _tasks[task_id] = task
    return _task_to_response(task)


@router.get(
    "/active",
    response_model=list[TaskResponse],
    summary="List active tasks",
)
async def list_active_tasks() -> list[TaskResponse]:
    """Return all tasks whose status is not terminal (pending | running).

    Useful for dashboards that need to display in-progress work without
    pulling the full task list.
    """
    active = [_task_to_response(t) for t in _tasks.values() if t["status"] not in _TERMINAL_STATES]
    return active


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task status",
)
async def get_task(task_id: str) -> TaskResponse:
    """Get the current status, progress, and result of a single task.

    Raises 404 if no task with the given identifier exists.
    """
    task = _get_task_or_404(task_id)
    return _task_to_response(task)


@router.post(
    "/{task_id}/cancel",
    response_model=TaskResponse,
    summary="Cancel a task",
)
async def cancel_task(task_id: str) -> TaskResponse:
    """Request cancellation of a running or pending task.

    The transition is immediate – the task moves to the *cancelled* state.
    If the task is already in a terminal state a 409 Conflict is returned.
    """
    task = _get_task_or_404(task_id)

    if task["status"] in _TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail=(f"Task {task_id!r} is already in terminal state '{task['status']}' and cannot be cancelled"),
        )

    task["status"] = "cancelled"
    task["updated_at"] = time.time()
    return _task_to_response(task)


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="List all tasks with pagination",
)
async def list_tasks(
    offset: int = Query(0, ge=0, description="Number of tasks to skip from the start"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tasks to return"),
) -> TaskListResponse:
    """List all tasks ordered by creation time (newest first).

    Supports ``offset`` / ``limit`` pagination.
    """
    all_tasks = sorted(_tasks.values(), key=lambda t: t.get("created_at", 0), reverse=True)
    total = len(all_tasks)
    sliced = all_tasks[offset : offset + limit]

    return TaskListResponse(
        tasks=[_task_to_response(t) for t in sliced],
        total=total,
        offset=offset,
        limit=limit,
    )
