"""Tests for history router — GET /api/history, DELETE /api/history/{task_id}."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

MOCK_HISTORY = [
    {
        "id": 1,
        "task_id": "task-001",
        "model_name": "unet",
        "area_km2": 1.5,
        "created_at": "2025-01-01T00:00:00",
        "mask_path": "/tmp/m/task-001.png",
        "overlay_path": None,
        "image_path": None,
        "thumbnail_path": None,
        "status": "completed",
    },
    {
        "id": 2,
        "task_id": "task-002",
        "model_name": "ndsi",
        "area_km2": 2.3,
        "created_at": "2025-01-02T00:00:00",
        "mask_path": "/tmp/m/task-002.png",
        "overlay_path": "/tmp/o/task-002.png",
        "image_path": "/tmp/i/task-002.tif",
        "thumbnail_path": "/tmp/t/task-002.png",
        "status": "completed",
    },
]


class TestListHistory:
    """Tests for GET /api/history."""

    @patch("app.routers.history.get_history")
    @patch("app.routers.history.path_to_url")
    def test_list_history_returns_rows(self, mock_url, mock_get):
        mock_get.return_value = MOCK_HISTORY
        mock_url.side_effect = lambda p: f"/files/{Path(p).name}"

        from app.routers.history import list_history

        result = list_history(limit=50, offset=0)
        assert len(result) == 2
        assert result[0]["task_id"] == "task-001"

    @patch("app.routers.history.get_history")
    @patch("app.routers.history.path_to_url")
    def test_list_history_paths_converted(self, mock_url, mock_get):
        mock_get.return_value = MOCK_HISTORY
        mock_url.side_effect = lambda p: f"URL({p})"

        from app.routers.history import list_history

        result = list_history(limit=50, offset=0)
        assert result[0]["mask_path"].startswith("URL(")
        assert result[1]["overlay_path"].startswith("URL(")
        assert result[1]["image_path"].startswith("URL(")
        assert result[1]["thumbnail_path"].startswith("URL(")

    @patch("app.routers.history.get_history")
    @patch("app.routers.history.path_to_url")
    def test_list_history_empty(self, mock_url, mock_get):
        mock_get.return_value = []

        from app.routers.history import list_history

        result = list_history(limit=50, offset=0)
        assert result == []

    @patch("app.routers.history.get_history")
    def test_list_history_passes_limit_offset(self, mock_get):
        mock_get.return_value = []

        from app.routers.history import list_history

        list_history(limit=10, offset=20)
        mock_get.assert_called_once_with(10, 20)

    @patch("app.routers.history.get_history")
    @patch("app.routers.history.path_to_url")
    def test_list_history_none_paths_skipped(self, mock_url, mock_get):
        mock_get.return_value = [{"task_id": "x", "mask_path": None, "overlay_path": None}]
        mock_url.side_effect = lambda p: f"URL({p})"

        from app.routers.history import list_history

        result = list_history(limit=50, offset=0)
        assert result[0]["mask_path"] is None


class TestRemoveHistory:
    """Tests for DELETE /api/history/{task_id}."""

    @patch("app.routers.history.delete_result")
    def test_remove_history_success(self, mock_del):
        mock_del.return_value = True

        from app.routers.history import remove_history

        result = remove_history(task_id="task-001")
        assert result == {"ok": True}
        mock_del.assert_called_once_with("task-001")

    @patch("app.routers.history.delete_result")
    def test_remove_history_not_found(self, mock_del):
        mock_del.return_value = False

        from fastapi import HTTPException

        from app.routers.history import remove_history

        with pytest.raises(HTTPException) as exc_info:
            remove_history(task_id="nonexistent")
        assert exc_info.value.status_code == 404
