"""Tests for dashboard and pipeline routers."""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))


class TestDashboardRouter:
    def test_dashboard_stats_shape(self):
        from app.routers.dashboard import dashboard_stats

        result = asyncio.run(dashboard_stats())
        assert "total_segments" in result
        assert "total_area_km2" in result
        assert "model_usage" in result
        assert "recent_tasks" in result


class TestPipelineRouter:
    def test_list_pipeline_runs(self):
        from app.routers.pipeline import list_runs

        result = asyncio.run(list_runs(q=None, status=None))
        runs = result["runs"]
        assert isinstance(runs, list)
        assert len(runs) >= 1
        assert "id" in runs[0]
        assert "stages" in runs[0]

    def test_cancel_unknown_run(self):
        from fastapi import HTTPException

        from app.routers.pipeline import cancel_run

        with pytest.raises(HTTPException) as exc:
            asyncio.run(cancel_run("nonexistent-run-id"))
        assert exc.value.status_code == 404
