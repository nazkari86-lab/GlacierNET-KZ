"""Tests for trend router — POST /api/trend."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

MOCK_TREND_RESULT = {
    "data": [
        {"year": 2015, "area_km2": 5.0},
        {"year": 2020, "area_km2": 4.5},
    ],
    "forecast": [
        {"year": 2030, "area_km2": 4.0, "ci_lower": 3.8, "ci_upper": 4.2},
        {"year": 2050, "area_km2": 3.0, "ci_lower": 2.5, "ci_upper": 3.5},
    ],
    "loss_rate_km2_per_year": 0.1,
    "total_loss_percent": 10.0,
    "r_squared": 0.95,
    "p_value": 0.01,
    "significant": True,
}


class TestTrendEndpoint:
    """Tests for POST /api/trend."""

    @patch("app.routers.trend.get_result")
    @patch("app.routers.trend.compute_trend")
    def test_trend_success(self, mock_trend, mock_get):
        mock_get.side_effect = [
            {"task_id": "a", "area_km2": 5.0},
            {"task_id": "b", "area_km2": 4.5},
        ]
        mock_trend.return_value = MOCK_TREND_RESULT

        from app.routers.trend import trend_analysis
        from app.schemas.requests import TrendRequest

        req = TrendRequest(file_ids=["a", "b"], years=[2015, 2020], forecast_until=2050)
        result = trend_analysis(req)

        assert result["loss_rate_km2_per_year"] == 0.1
        assert result["significant"] is True
        mock_trend.assert_called_once_with([2015, 2020], [5.0, 4.5], 2050)

    @patch("app.routers.trend.get_result")
    def test_trend_result_not_found(self, mock_get):
        mock_get.return_value = None

        from fastapi import HTTPException

        from app.routers.trend import trend_analysis
        from app.schemas.requests import TrendRequest

        req = TrendRequest(file_ids=["missing1", "missing2"], years=[2015, 2020], forecast_until=2050)
        with pytest.raises(HTTPException) as exc_info:
            trend_analysis(req)
        assert exc_info.value.status_code == 404

    @patch("app.routers.trend.get_result")
    def test_trend_no_area_data(self, mock_get):
        mock_get.return_value = {"task_id": "a", "area_km2": None}

        from fastapi import HTTPException

        from app.routers.trend import trend_analysis
        from app.schemas.requests import TrendRequest

        req = TrendRequest(file_ids=["a", "b"], years=[2015, 2020], forecast_until=2050)
        with pytest.raises(HTTPException) as exc_info:
            trend_analysis(req)
        assert exc_info.value.status_code == 404

    @patch("app.routers.trend.get_result")
    @patch("app.routers.trend.compute_trend")
    def test_trend_passes_forecast_until(self, mock_trend, mock_get):
        mock_get.side_effect = [
            {"task_id": "a", "area_km2": 5.0},
            {"task_id": "b", "area_km2": 4.5},
        ]
        mock_trend.return_value = MOCK_TREND_RESULT

        from app.routers.trend import trend_analysis
        from app.schemas.requests import TrendRequest

        req = TrendRequest(file_ids=["a", "b"], years=[2015, 2020], forecast_until=2040)
        trend_analysis(req)

        call_args = mock_trend.call_args
        assert call_args[0][2] == 2040

    def test_trend_request_validation(self):
        from pydantic import ValidationError

        from app.schemas.requests import TrendRequest

        with pytest.raises(ValidationError):
            TrendRequest(file_ids=["a"], years=[2020])

        with pytest.raises(ValidationError):
            TrendRequest(file_ids=[], years=[2020])
