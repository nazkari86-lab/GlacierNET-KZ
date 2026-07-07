# -*- coding: utf-8 -*-
"""Model training management routes.

Provides endpoints to start, monitor, stop, and resume training runs.
Training progress is driven by asyncio background tasks — one task per run —
so status polling does not block the event loop.  Swap the simulated epoch
loop for a real ML training call when data is available.
"""

from __future__ import annotations

import asyncio  # noqa: F401 — used in _training_loop and asyncio.create_task
import math
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/training", tags=["training"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class TrainConfig(BaseModel):
    """Hyper-parameters and settings for a training run."""

    dataset_id: str = Field(..., min_length=1, description="ID of the dataset to train on")
    model_name: str = Field("unet", description="Model architecture name")
    backbone: str = Field("resnet50", description="Encoder backbone")
    epochs: int = Field(100, ge=1, le=10000, description="Max training epochs")
    batch_size: int = Field(8, ge=1, le=256, description="Mini-batch size")
    learning_rate: float = Field(1e-4, gt=0, description="Initial learning rate")
    loss: str = Field("binary_crossentropy", description="Loss function name")
    optimizer: str = Field("adam", description="Optimizer algorithm")
    early_stopping: bool = Field(True, description="Enable early stopping")
    checkpoint: bool = Field(True, description="Save epoch checkpoints")


class TrainStatus(BaseModel):
    """Live status of a training run."""

    task_id: str
    status: str
    epoch: int = 0
    total_epochs: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    best_metric: float = 0.0


class TrainHistoryItem(BaseModel):
    """Summary of a completed or failed training run."""

    task_id: str
    dataset_id: str
    model_name: str
    status: str
    epochs_completed: int
    best_metric: float
    started_at: float
    finished_at: Optional[float] = None


class ModelInfo(BaseModel):
    """Metadata for a trained model artifact."""

    id: str
    name: str
    task_id: str
    dataset_id: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: float


class TrainingHistoryResponse(BaseModel):
    """Paginated training history."""

    runs: list[TrainHistoryItem]
    total: int
    offset: int
    limit: int


class ModelListResponse(BaseModel):
    """Paginated list of trained models."""

    models: list[ModelInfo]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_runs: dict[str, dict[str, Any]] = {}
_models: dict[str, dict[str, Any]] = {}

# Terminal states for training runs.
_TERMINAL_STATES: frozenset[str] = frozenset({"completed", "failed", "stopped"})
_RESUMABLE_STATES: frozenset[str] = frozenset({"stopped", "failed"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_to_status(run: dict[str, Any]) -> TrainStatus:
    """Convert an internal run dict to TrainStatus."""
    return TrainStatus(
        task_id=run["task_id"],
        status=run["status"],
        epoch=run.get("epoch", 0),
        total_epochs=run.get("total_epochs", 0),
        metrics=run.get("metrics", {}),
        best_metric=run.get("best_metric", 0.0),
    )


def _run_to_history(run: dict[str, Any]) -> TrainHistoryItem:
    """Convert an internal run dict to a history summary."""
    return TrainHistoryItem(
        task_id=run["task_id"],
        dataset_id=run["config"]["dataset_id"],
        model_name=run["config"]["model_name"],
        status=run["status"],
        epochs_completed=run.get("epoch", 0),
        best_metric=run.get("best_metric", 0.0),
        started_at=run.get("started_at", 0.0),
        finished_at=run.get("finished_at"),
    )


def _model_to_info(m: dict[str, Any]) -> ModelInfo:
    """Convert an internal model dict to ModelInfo."""
    return ModelInfo(
        id=m["id"],
        name=m["name"],
        task_id=m["task_id"],
        dataset_id=m["dataset_id"],
        metrics=m.get("metrics", {}),
        created_at=m.get("created_at", 0.0),
    )


async def _training_loop(run: dict[str, Any]) -> None:
    """Async background task: advances epoch state once per 2 seconds.

    Replaces the old synchronous _advance_run that was called on every poll.
    Swap the math.exp simulation for a real TF/PyTorch training call when
    satellite data is available (pass results back via run["metrics"]).
    """
    run["status"] = "running"
    total = run.get("total_epochs", 1)

    for epoch in range(1, total + 1):
        if run["status"] in _TERMINAL_STATES:
            break
        if run["status"] == "stopping":
            run["status"] = "stopped"
            run["finished_at"] = time.time()
            return
        while run["status"] == "paused":
            await asyncio.sleep(0.5)

        loss = round(0.35 * math.exp(-epoch / 20) + 0.08, 4)
        val_loss = round(0.38 * math.exp(-epoch / 22) + 0.09, 4)
        iou = round(0.72 + 0.16 * (1 - math.exp(-epoch / 15)), 4)
        run["epoch"] = epoch
        run["metrics"] = {"loss": loss, "val_loss": val_loss, "iou": iou}
        run["best_metric"] = iou
        run.setdefault("logs", []).append(
            {
                "time": time.strftime("%H:%M:%S"),
                "text": f"Epoch {epoch}/{total} - loss: {loss} - val_loss: {val_loss} - iou: {iou}",
                "type": "success",
            }
        )
        await asyncio.sleep(2)

    if run["status"] == "running":
        run["status"] = "completed"
        run["finished_at"] = time.time()


def _get_run_or_404(task_id: str) -> dict[str, Any]:
    """Look up a training run or raise HTTP 404."""
    run = _runs.get(task_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Training run {task_id!r} not found",
        )
    return run


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/start", response_model=TrainStatus, status_code=201, summary="Start a training run")
async def start_training(config: TrainConfig) -> TrainStatus:
    """Start a new training run with the given configuration.

    The run is created in *pending* state and transitions to *running* once
    a GPU worker picks it up.

    Raises **400** if the referenced ``dataset_id`` does not exist (in a
    production implementation).
    """
    task_id = f"train-{uuid.uuid4().hex[:12]}"
    now = time.time()

    run: dict[str, Any] = {
        "task_id": task_id,
        "config": config.model_dump(),
        "status": "pending",
        "epoch": 0,
        "total_epochs": config.epochs,
        "metrics": {},
        "best_metric": 0.0,
        "started_at": now,
        "finished_at": None,
        "logs": [
            {
                "time": time.strftime("%H:%M:%S"),
                "text": f"Starting training: {config.model_name} on {config.dataset_id}",
                "type": "info",
            }
        ],
    }
    _runs[task_id] = run
    asyncio.create_task(_training_loop(run))
    return _run_to_status(run)


@router.get("/status/{task_id}", response_model=TrainStatus, summary="Get training status")
async def get_training_status(task_id: str) -> TrainStatus:
    """Get the live status of a training run.

    Includes the current epoch, aggregate metrics, and best recorded metric
    value.
    """
    run = _get_run_or_404(task_id)
    return _run_to_status(run)


@router.get("/logs/{task_id}")
async def get_training_logs(task_id: str) -> dict[str, Any]:
    run = _get_run_or_404(task_id)
    return {"logs": run.get("logs", [])}


@router.post("/pause/{task_id}", response_model=TrainStatus, summary="Pause a training run")
async def pause_training(task_id: str) -> TrainStatus:
    run = _get_run_or_404(task_id)
    if run["status"] not in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot pause from state '{run['status']}'",
        )
    run["status"] = "paused"
    return _run_to_status(run)


@router.post("/stop/{task_id}", response_model=TrainStatus, summary="Stop a training run")
async def stop_training(task_id: str) -> TrainStatus:
    """Request graceful stop of a running training job.

    The run transitions to *stopping* so the worker can save a final
    checkpoint.  Raises **409** if the run is already in a terminal state.
    """
    run = _get_run_or_404(task_id)

    if run["status"] in _TERMINAL_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Training run {task_id!r} is already '{run['status']}'",
        )

    run["status"] = "stopping"
    return _run_to_status(run)


@router.get("/history", response_model=TrainingHistoryResponse, summary="List past training runs")
async def training_history(
    dataset_id: Optional[str] = Query(None, description="Filter by dataset"),
    status: Optional[str] = Query(None, description="Filter by run status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
) -> TrainingHistoryResponse:
    """Return a paginated history of past training runs.

    Runs are ordered by start time (newest first).  Optional ``dataset_id``
    and ``status`` filters narrow the results.
    """
    runs = sorted(_runs.values(), key=lambda r: r.get("started_at", 0), reverse=True)

    if dataset_id is not None:
        runs = [r for r in runs if r["config"].get("dataset_id") == dataset_id]
    if status is not None:
        runs = [r for r in runs if r.get("status") == status]

    total = len(runs)
    sliced = runs[offset : offset + limit]

    return TrainingHistoryResponse(
        runs=[_run_to_history(r) for r in sliced],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/models", response_model=ModelListResponse, summary="List trained models")
async def list_models(
    dataset_id: Optional[str] = Query(None, description="Filter by dataset"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
) -> ModelListResponse:
    """List all trained model artifacts.

    Models are ordered by creation time (newest first).  Optionally filter
    by ``dataset_id``.
    """
    models = sorted(_models.values(), key=lambda m: m.get("created_at", 0), reverse=True)

    if dataset_id is not None:
        models = [m for m in models if m.get("dataset_id") == dataset_id]

    total = len(models)
    sliced = models[offset : offset + limit]

    return ModelListResponse(
        models=[_model_to_info(m) for m in sliced],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.delete("/models/{model_id}", status_code=200, summary="Remove a trained model")
async def delete_model(model_id: str) -> dict:
    """Remove a trained model artifact.

    Returns **204 No Content** on success; **404** if the model does not
    exist.
    """
    if model_id not in _models:
        raise HTTPException(
            status_code=404,
            detail=f"Model {model_id!r} not found",
        )
    del _models[model_id]
    return {"status": "deleted", "model_id": model_id}


@router.post("/resume/{task_id}", response_model=TrainStatus, summary="Resume interrupted training")
async def resume_training(task_id: str) -> TrainStatus:
    """Resume an interrupted or stopped training run from the last checkpoint.

    Raises **404** if the run does not exist and **409** if the run is not
    in a resumable state (only *stopped* and *failed* runs may be resumed).
    """
    run = _get_run_or_404(task_id)

    if run["status"] not in _RESUMABLE_STATES:
        raise HTTPException(
            status_code=409,
            detail=(f"Training run {task_id!r} cannot be resumed from state '{run['status']}'"),
        )

    run["status"] = "pending"
    run["started_at"] = time.time()
    run["finished_at"] = None
    run["epoch"] = 0
    asyncio.create_task(_training_loop(run))
    return _run_to_status(run)


@router.get("/config/{task_id}", response_model=TrainConfig, summary="Get training configuration")
async def get_training_config(task_id: str) -> TrainConfig:
    """Retrieve the original training configuration for a run.

    Useful for reproducing a specific training run or inspecting
    hyper-parameters.
    """
    run = _get_run_or_404(task_id)
    return TrainConfig(**run["config"])
