"""Tests for tasks router — task CRUD, list, cancel, pagination."""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.routers.tasks import (
    TaskCreate,
    _tasks,
    cancel_task,
    create_task,
    get_task,
    list_active_tasks,
    list_tasks,
)


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear in-memory task store between tests."""
    _tasks.clear()
    yield
    _tasks.clear()


def _seed_task(task_id: str, name: str = "test-task", status: str = "pending"):
    _tasks[task_id] = {
        "id": task_id,
        "name": name,
        "description": "",
        "priority": "normal",
        "metadata": {},
        "status": status,
        "progress": 0.0,
        "result": None,
        "error": None,
        "created_at": 1700000000.0,
        "updated_at": 1700000000.0,
    }


def _seed_tasks(n: int, status: str = "pending"):
    for i in range(n):
        _seed_task(f"task-{i:03d}", name=f"task-{i}", status=status)


class TestListTasks:
    def test_empty(self):
        result = asyncio.run(list_tasks(offset=0, limit=20))
        assert result.total == 0
        assert result.tasks == []

    def test_returns_all(self):
        _seed_tasks(5)
        result = asyncio.run(list_tasks(offset=0, limit=20))
        assert result.total == 5
        assert len(result.tasks) == 5

    def test_pagination_limit(self):
        _seed_tasks(10)
        result = asyncio.run(list_tasks(offset=0, limit=3))
        assert len(result.tasks) == 3

    def test_pagination_offset(self):
        _seed_tasks(10)
        result = asyncio.run(list_tasks(offset=5, limit=3))
        assert len(result.tasks) == 3


class TestGetTask:
    def test_found(self):
        _seed_task("abc-123")
        result = asyncio.run(get_task(task_id="abc-123"))
        assert result.id == "abc-123"

    def test_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_task(task_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestCancelTask:
    def test_cancel_pending(self):
        _seed_task("abc-123", status="pending")
        result = asyncio.run(cancel_task(task_id="abc-123"))
        assert result.status == "cancelled"

    def test_cancel_completed_fails(self):
        from fastapi import HTTPException
        _seed_task("abc-123", status="completed")
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(cancel_task(task_id="abc-123"))
        assert exc_info.value.status_code == 409

    def test_cancel_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(cancel_task(task_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestCreateTask:
    def test_create(self):
        body = TaskCreate(name="segmentation-job", description="Run on dataset A")
        result = asyncio.run(create_task(body=body))
        assert result.status == "pending"
        assert result.name == "segmentation-job"
        assert result.id in _tasks

    def test_create_stores_task(self):
        body = TaskCreate(name="area-calc")
        result = asyncio.run(create_task(body=body))
        assert _tasks[result.id]["status"] == "pending"


class TestListActiveTasks:
    def test_returns_only_active(self):
        _seed_task("t1", status="pending")
        _seed_task("t2", status="running")
        _seed_task("t3", status="completed")
        result = asyncio.run(list_active_tasks())
        assert len(result) == 2
        ids = [t.id for t in result]
        assert "t1" in ids
        assert "t2" in ids
        assert "t3" not in ids
