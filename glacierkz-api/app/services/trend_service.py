import numpy as np

from app.utils import resolve_core_dir

CORE_DIR = resolve_core_dir(__file__)

from src.metrics import forecast_to_2050 as core_forecast_to_2050  # noqa: E402
from src.metrics import trend_analysis as core_trend_analysis  # noqa: E402


def compute_trend(years: list[int], areas: list[float], forecast_until: int = 2050) -> dict:
    years_arr = np.asarray(years)
    areas_arr = np.asarray(areas)

    trend = core_trend_analysis(years_arr, areas_arr)

    data = [{"year": int(yi), "area_km2": round(ai, 4)} for yi, ai in zip(years, areas)]

    future_years, predicted, ci_lower, ci_upper, _ = core_forecast_to_2050(
        years_arr, areas_arr, target_year=forecast_until
    )
    forecast = [
        {"year": int(yi), "area_km2": round(max(0, pi), 4), "ci_lower": round(max(0, li), 4), "ci_upper": round(ui, 4)}
        for yi, pi, li, ui in zip(future_years, predicted, ci_lower, ci_upper)
    ]

    total_loss_percent = trend["change_percent"]
    if not np.isfinite(total_loss_percent):
        total_loss_percent = 0.0

    return {
        "data": data,
        "forecast": forecast,
        "loss_rate_km2_per_year": round(abs(trend["slope_km2_per_year"]), 4),
        "total_loss_percent": round(float(total_loss_percent), 2),
        "r_squared": round(trend["r_squared"], 4),
        "p_value": round(trend["p_value"], 6),
        "significant": trend["significant"],
    }
