"""Tests for training router — start, status, stop, resume, history, models, config."""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.routers.training import (
    TrainConfig,
    _models,
    _runs,
    get_training_config,
    get_training_status,
    list_models,
    resume_training,
    start_training,
    stop_training,
    training_history,
)


@pytest.fixture(autouse=True)
def clear_runs():
    """Clear in-memory training runs between tests."""
    _runs.clear()
    _models.clear()
    yield
    _runs.clear()
    _models.clear()


def _seed_run(task_id: str, status: str = "running", epoch: int = 5, total_epochs: int = 50):
    _runs[task_id] = {
        "task_id": task_id,
        "config": {
            "model_name": "unet",
            "dataset_id": "ds-001",
            "epochs": total_epochs,
            "learning_rate": 1e-4,
            "batch_size": 8,
            "optimizer": "adam",
            "loss": "binary_crossentropy",
            "backbone": "resnet50",
            "early_stopping": True,
            "checkpoint": True,
        },
        "status": status,
        "epoch": epoch,
        "total_epochs": total_epochs,
        "metrics": {"loss": 0.15, "iou": 0.82},
        "best_metric": 0.82,
        "started_at": 1700000000.0,
        "finished_at": None,
    }


def _seed_model(model_id: str):
    _models[model_id] = {
        "id": model_id,
        "name": "unet-best",
        "task_id": "train-001",
        "dataset_id": "ds-001",
        "metrics": {"iou": 0.85},
        "created_at": 1700000000.0,
    }


class TestStartTraining:
    def test_start_success(self):
        config = TrainConfig(model_name="unet", dataset_id="ds-001", epochs=50)
        result = asyncio.run(start_training(config=config))
        assert result.status in ("pending", "running", "queued")
        assert result.task_id in _runs

    def test_start_stores_run(self):
        config = TrainConfig(model_name="deeplab", dataset_id="ds-002", epochs=10)
        result = asyncio.run(start_training(config=config))
        assert _runs[result.task_id]["config"]["model_name"] == "deeplab"


class TestGetTrainingStatus:
    def test_found(self):
        _seed_run("train-001")
        result = asyncio.run(get_training_status(task_id="train-001"))
        assert result.task_id == "train-001"

    def test_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_training_status(task_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestStopTraining:
    def test_stop_running(self):
        _seed_run("train-001", status="running")
        result = asyncio.run(stop_training(task_id="train-001"))
        assert result.status == "stopping"

    def test_stop_completed_fails(self):
        from fastapi import HTTPException
        _seed_run("train-001", status="completed")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(stop_training(task_id="train-001"))
        assert exc_info.value.status_code == 409

    def test_stop_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(stop_training(task_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestResumeTraining:
    def test_resume_stopped(self):
        _seed_run("train-001", status="stopped")
        result = asyncio.run(resume_training(task_id="train-001"))
        assert result.status == "pending"

    def test_resume_failed(self):
        _seed_run("train-001", status="failed")
        result = asyncio.run(resume_training(task_id="train-001"))
        assert result.status == "pending"

    def test_resume_running_fails(self):
        from fastapi import HTTPException
        _seed_run("train-001", status="running")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resume_training(task_id="train-001"))
        assert exc_info.value.status_code == 409

    def test_resume_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resume_training(task_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestTrainingHistory:
    def test_empty_history(self):
        result = asyncio.run(training_history(dataset_id=None, status=None, offset=0, limit=20))
        assert result.total == 0
        assert result.runs == []

    def test_with_runs(self):
        _seed_run("train-001")
        _seed_run("train-002")
        result = asyncio.run(training_history(dataset_id=None, status=None, offset=0, limit=20))
        assert result.total == 2

    def test_pagination(self):
        for i in range(10):
            _seed_run(f"train-{i:03d}")
        result = asyncio.run(training_history(dataset_id=None, status=None, limit=3, offset=2))
        assert len(result.runs) == 3

    def test_filter_by_status(self):
        _seed_run("train-001", status="completed")
        _seed_run("train-002", status="running")
        result = asyncio.run(training_history(dataset_id=None, status="completed", offset=0, limit=20))
        assert result.total == 1


class TestListModels:
    def test_empty_models(self):
        result = asyncio.run(list_models(dataset_id=None, offset=0, limit=20))
        assert result.total == 0
        assert result.models == []

    def test_with_models(self):
        _seed_model("model-001")
        _seed_model("model-002")
        result = asyncio.run(list_models(dataset_id=None, offset=0, limit=20))
        assert result.total == 2

    def test_pagination(self):
        result = asyncio.run(list_models(dataset_id=None, limit=5, offset=0))
        assert isinstance(result.models, list)


class TestGetTrainingConfig:
    def test_found(self):
        _seed_run("train-001")
        result = asyncio.run(get_training_config(task_id="train-001"))
        assert result.model_name == "unet"
        assert result.dataset_id == "ds-001"

    def test_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_training_config(task_id="nonexistent"))
        assert exc_info.value.status_code == 404
