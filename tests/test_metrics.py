"""Tests for src/metrics.py."""

import numpy as np
import pytest

from src.metrics import (
    evaluate_segmentation,
    forecast_to_2050,
    ice_volume_loss_to_water_supply,
    pixels_to_area_km2,
    rmse_against_wgms,
    trend_analysis,
)


class TestEvaluateSegmentation:
    def test_perfect_prediction(self):
        y = np.array([0, 0, 1, 1, 1])
        result = evaluate_segmentation(y, y)
        assert result["f1"] == pytest.approx(1.0)
        assert result["precision"] == pytest.approx(1.0)
        assert result["recall"] == pytest.approx(1.0)
        assert result["iou"] == pytest.approx(1.0)

    def test_all_wrong(self):
        y_true = np.array([1, 1, 1])
        y_pred = np.array([0, 0, 0])
        result = evaluate_segmentation(y_true, y_pred)
        assert result["recall"] == pytest.approx(0.0)
        assert result["precision"] == pytest.approx(0.0)

    def test_2d_input(self):
        y_true = np.ones((10, 10))
        y_pred = np.ones((10, 10))
        result = evaluate_segmentation(y_true, y_pred)
        assert result["f1"] == pytest.approx(1.0)

    def test_partial_overlap(self):
        y_true = np.array([1, 1, 0, 0])
        y_pred = np.array([1, 0, 0, 1])
        result = evaluate_segmentation(y_true, y_pred)
        assert result["precision"] == pytest.approx(0.5)
        assert result["recall"] == pytest.approx(0.5)


class TestPixelsToAreaKm2:
    def test_known_value(self):
        # 100 pixels * 100 m^2 = 10000 m^2 = 0.01 km^2
        assert pixels_to_area_km2(100, 100.0) == pytest.approx(0.01)

    def test_zero_pixels(self):
        assert pixels_to_area_km2(0, 100.0) == 0.0

    def test_sentinel_pixel(self):
        # Sentinel-2: 10m pixel = 100 m^2
        result = pixels_to_area_km2(1000, 100.0)
        assert result == pytest.approx(0.1)


class TestTrendAnalysis:
    def test_clear_decreasing_trend(self):
        years = [2000, 2005, 2010, 2015, 2020]
        areas = [10.0, 9.0, 8.0, 7.0, 6.0]
        result = trend_analysis(years, areas)
        assert result["slope_km2_per_year"] < 0
        assert result["r_squared"] == pytest.approx(1.0, abs=1e-10)
        assert result["significant"] is True
        assert result["change_km2"] == pytest.approx(-4.0)
        assert result["change_percent"] == pytest.approx(-40.0)

    def test_increasing_trend(self):
        years = [2000, 2005, 2010]
        areas = [5.0, 6.0, 7.0]
        result = trend_analysis(years, areas)
        assert result["slope_km2_per_year"] > 0

    def test_single_point_returns_nan(self):
        """linregress with n=1 cannot compute slope — returns NaN."""
        result = trend_analysis([2020], [5.0])
        assert np.isnan(result["slope_km2_per_year"])


class TestForecastTo2050:
    def test_returns_correct_length(self):
        years = [2000, 2010, 2020]
        areas = [10.0, 8.0, 6.0]
        future_years, pred, ci_lo, ci_hi, trend = forecast_to_2050(years, areas)
        assert future_years[0] == 2020
        assert future_years[-1] == 2050
        assert len(future_years) == len(pred)
        assert np.all(ci_lo <= pred)
        assert np.all(pred <= ci_hi)

    def test_trend_passed_through(self):
        years = [2000, 2010, 2020]
        areas = [10.0, 8.0, 6.0]
        _, _, _, _, trend = forecast_to_2050(years, areas)
        assert "slope_km2_per_year" in trend
        assert "r_squared" in trend


class TestRmseAgainstWgms:
    def test_perfect_match(self):
        pred = {2010: 5.0, 2015: 4.0}
        wgms = {2010: 5.0, 2015: 4.0}
        rmse, years, diffs = rmse_against_wgms(pred, wgms)
        assert rmse == pytest.approx(0.0)
        assert years == [2010, 2015]

    def test_known_rmse(self):
        pred = {2010: 6.0}
        wgms = {2010: 4.0}
        rmse, _, _ = rmse_against_wgms(pred, wgms)
        assert rmse == pytest.approx(2.0)

    def test_no_common_years(self):
        with pytest.raises(ValueError):
            rmse_against_wgms({2010: 1.0}, {2020: 1.0})


class TestIceVolumeLoss:
    def test_known_value(self):
        result = ice_volume_loss_to_water_supply(
            area_loss_km2=1.0,
            mean_ice_thickness_m=30.0,
            population=2_400_000,
            per_capita_liters_per_day=400.0,
        )
        # 1 km^2 * 30m = 30e6 m^3 ice
        # water = 30e6 * 0.9 = 27e6 m^3 = 27e9 L
        # daily demand = 2.4e6 * 400 = 960e6 L
        # days = 27e9 / 960e6 = 28.125
        assert result["days_of_supply_equivalent"] == pytest.approx(28.125)
        assert result["years_of_supply_equivalent"] == pytest.approx(28.125 / 365.25)

    def test_keys_present(self):
        result = ice_volume_loss_to_water_supply(1.0)
        assert "volume_water_m3" in result
        assert "city_daily_demand_liters" in result
        assert "days_of_supply_equivalent" in result
        assert "years_of_supply_equivalent" in result
