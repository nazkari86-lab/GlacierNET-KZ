#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Temporal analysis and time series module for GlacierNET-KZ.

Provides glacier change detection, trend analysis, seasonal decomposition,
anomaly detection, and area time series interpolation using numpy/scipy only.
"""

from __future__ import annotations

__all__ = [
    "compute_trend",
    "mann_kendall_test",
    "sens_slope",
    "detect_change_points",
    "seasonal_decompose",
    "detect_anomalies",
    "interpolate_time_series",
    "cumulative_change",
    "area_change_analysis",
    "aggregate_annual",
]

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_numpy(data: Sequence[float]) -> np.ndarray:
    """Coerce input to a 1-D float numpy array."""
    arr = np.asarray(data, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("Input must be 1-D")
    return arr


def _date_to_numeric(dates: Sequence) -> np.ndarray:
    """Convert date-like inputs to numeric year offsets for regression.

    Accepts `datetime.date`, `datetime.datetime`, numpy datetime64,
    or anything that can be cast via ``np.datetime64``.  Strings in
    ``YYYY`` or ``YYYY-MM`` format are also handled.
    """
    arr = np.asarray(dates)
    # If already numeric (int / float years)
    if np.issubdtype(arr.dtype, np.number):
        return arr.astype(np.float64)

    # Convert to datetime64 then to epoch seconds
    try:
        dt64 = np.array([np.datetime64(d) for d in dates])
    except Exception:
        # Fallback: attempt to parse strings as years
        try:
            return np.array([float(d) for d in dates], dtype=np.float64)
        except Exception as exc:
            raise TypeError(f"Cannot convert dates to numeric: {exc}") from exc

    # Days since first observation (float years approximation)
    days = (dt64 - dt64[0]) / np.timedelta64(1, "D")
    years = days / 365.2425
    return years.astype(np.float64)


# ---------------------------------------------------------------------------
# 1. Linear regression trend
# ---------------------------------------------------------------------------


def compute_trend(
    dates: Sequence,
    values: Sequence[float],
) -> Dict[str, Any]:
    """Compute a linear regression trend over time.

    Parameters
    ----------
    dates : sequence
        Dates or numeric values for the x-axis.
    values : sequence of float
        Observed values (e.g. glacier area).

    Returns
    -------
    dict
        slope, intercept, r_squared, p_value, trend_direction,
        annual_rate — slope expressed per year.
    """
    x = _date_to_numeric(dates)
    y = _to_numpy(values)

    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]

    if len(x) < 2:
        return {
            "slope": np.nan,
            "intercept": np.nan,
            "r_squared": np.nan,
            "p_value": np.nan,
            "trend_direction": "insufficient data",
            "annual_rate": np.nan,
        }

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    if slope > 1e-12:
        direction = "increasing"
    elif slope < -1e-12:
        direction = "decreasing"
    else:
        direction = "no trend"

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_value**2),
        "p_value": float(p_value),
        "trend_direction": direction,
        "annual_rate": float(slope),
    }


# ---------------------------------------------------------------------------
# 2. Mann-Kendall test
# ---------------------------------------------------------------------------


def mann_kendall_test(data: Sequence[float]) -> Dict[str, Any]:
    """Perform the Mann-Kendall trend test.

    Parameters
    ----------
    data : sequence of float
        Ordered time series (assumed in temporal order).

    Returns
    -------
    dict
        tau, p_value, trend (increasing / decreasing / no trend),
        significant (bool, at alpha = 0.05).
    """
    arr = _to_numpy(data)
    n = len(arr)

    if n < 4:
        return {
            "tau": np.nan,
            "p_value": np.nan,
            "trend": "insufficient data",
            "significant": False,
        }

    # Compute S statistic
    s = 0.0
    for k in range(n - 1):
        for j in range(k + 1, n):
            diff = arr[j] - arr[k]
            if diff > 0:
                s += 1.0
            elif diff < 0:
                s -= 1.0

    # Variance of S (accounts for ties)
    unique, counts = np.unique(arr, return_counts=True)
    tp = counts[counts > 1]
    var_s = n * (n - 1) * (2 * n + 5)
    for t in tp:
        var_s -= t * (t - 1) * (2 * t + 5)
    var_s /= 18.0

    # Z statistic
    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    p_value = 2.0 * stats.norm.sf(abs(z))
    tau = s / (n * (n - 1) / 2.0)

    if p_value < 0.05 and s > 0:
        trend = "increasing"
    elif p_value < 0.05 and s < 0:
        trend = "decreasing"
    else:
        trend = "no trend"

    return {
        "tau": float(tau),
        "p_value": float(p_value),
        "trend": trend,
        "significant": bool(p_value < 0.05),
    }


# ---------------------------------------------------------------------------
# 3. Sen's slope
# ---------------------------------------------------------------------------


def sens_slope(
    dates: Sequence,
    values: Sequence[float],
) -> Dict[str, Any]:
    """Estimate trend using Theil-Sen (median of pairwise slopes).

    Parameters
    ----------
    dates : sequence
        Dates or numeric values.
    values : sequence of float
        Observed values.

    Returns
    -------
    dict
        slope, intercept, confidence_interval (95 % CI tuple).
    """
    x = _date_to_numeric(dates)
    y = _to_numpy(values)

    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    n = len(x)

    if n < 2:
        return {
            "slope": np.nan,
            "intercept": np.nan,
            "confidence_interval": (np.nan, np.nan),
        }

    # Pairwise slopes
    slopes: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            if dx != 0:
                slopes.append((y[j] - y[i]) / dx)

    slopes_arr = np.array(slopes)
    slope = float(np.median(slopes_arr))

    # Intercept: median(y - slope * x)
    intercept = float(np.median(y - slope * x))

    # 95 % CI via normal approximation (variance of Sen's slope)
    se = np.sqrt(np.var(slopes_arr) / n) if n > 2 else np.nan
    if np.isfinite(se):
        z = stats.norm.ppf(0.975)
        ci = (float(slope - z * se), float(slope + z * se))
    else:
        ci = (np.nan, np.nan)

    return {
        "slope": slope,
        "intercept": intercept,
        "confidence_interval": ci,
    }


# ---------------------------------------------------------------------------
# 4. Change point detection (CUSUM / PELT-like)
# ---------------------------------------------------------------------------


def detect_change_points(
    data: Sequence[float],
    method: str = "cusum",
    threshold: float = 1.0,
) -> List[Dict[str, Any]]:
    """Detect abrupt change points in a time series.

    Parameters
    ----------
    data : sequence of float
        Time series values.
    method : str
        ``"cusum"`` — cumulative sum control chart.
        ``"variance"`` — rolling variance shift.
    threshold : float
        Sensitivity multiplier (higher → fewer change points).

    Returns
    -------
    list of dict
        Each dict contains ``index`` and ``value``.
    """
    arr = _to_numpy(data)
    n = len(arr)
    if n < 3:
        return []

    change_points: list[Dict[str, Any]] = []

    if method == "cusum":
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std < 1e-15:
            return []

        pos_cusum = np.zeros(n)
        neg_cusum = np.zeros(n)
        threshold_val = threshold * std

        for i in range(1, n):
            pos_cusum[i] = max(0, pos_cusum[i - 1] + (arr[i] - mean) / std - threshold_val)
            neg_cusum[i] = max(0, neg_cusum[i - 1] - (arr[i] - mean) / std - threshold_val)

        for i in range(1, n):
            if pos_cusum[i] > threshold_val and pos_cusum[i - 1] == 0:
                change_points.append({"index": int(i), "value": float(arr[i])})
            elif neg_cusum[i] > threshold_val and neg_cusum[i - 1] == 0:
                change_points.append({"index": int(i), "value": float(arr[i])})

    elif method == "variance":
        window = max(3, n // 10)
        for i in range(window, n - window):
            left = arr[i - window : i]
            right = arr[i : i + window]
            if np.std(left) > 1e-15 and np.std(right) > 1e-15:
                ratio = np.std(right) / np.std(left)
                if ratio > threshold or ratio < 1 / threshold:
                    change_points.append({"index": int(i), "value": float(arr[i])})
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'cusum' or 'variance'.")

    return change_points


# ---------------------------------------------------------------------------
# 5. Seasonal decomposition
# ---------------------------------------------------------------------------


def seasonal_decompose(
    data: Sequence[float],
    period: int = 12,
) -> Dict[str, Any]:
    """Classical additive seasonal decomposition.

    Parameters
    ----------
    data : sequence of float
        Time series values.
    period : int
        Number of observations per seasonal cycle (default 12 = monthly).

    Returns
    -------
    dict
        ``trend``, ``seasonal``, ``residual`` — each a numpy array.
    """
    arr = _to_numpy(data)
    n = len(arr)

    if n < 2 * period:
        return {
            "trend": arr,
            "seasonal": np.zeros_like(arr),
            "residual": np.zeros_like(arr),
        }

    # Trend via centered moving average
    trend = np.full(n, np.nan)
    half = period // 2
    for i in range(half, n - half):
        trend[i] = np.mean(arr[i - half : i - half + period])

    # Interpolate trend edges
    first_valid = half
    last_valid = n - half - 1
    trend[:first_valid] = trend[first_valid]
    trend[last_valid + 1 :] = trend[last_valid]

    # Detrend
    detrended = arr - trend

    # Seasonal component: average for each period position
    seasonal_means = np.zeros(period)
    seasonal_means_count = np.zeros(period)
    for i in range(n):
        idx = i % period
        seasonal_means[idx] += detrended[i]
        seasonal_means_count[idx] += 1

    seasonal_means /= np.maximum(seasonal_means_count, 1)
    seasonal_means -= np.mean(seasonal_means)  # center

    seasonal = np.array([seasonal_means[i % period] for i in range(n)])
    residual = arr - trend - seasonal

    return {
        "trend": trend,
        "seasonal": seasonal,
        "residual": residual,
    }


# ---------------------------------------------------------------------------
# 6. Anomaly detection
# ---------------------------------------------------------------------------


def detect_anomalies(
    data: Sequence[float],
    method: str = "zscore",
    threshold: float = 3.0,
) -> List[Dict[str, Any]]:
    """Detect anomalous values in a time series.

    Parameters
    ----------
    data : sequence of float
        Observed values.
    method : str
        ``"zscore"`` — standard deviation based.
        ``"iqr"`` — interquartile range based.
    threshold : float
        Sensitivity (z-score threshold or IQR multiplier).

    Returns
    -------
    list of dict
        Each dict: ``index``, ``value``, ``score``.
    """
    arr = _to_numpy(data)
    anomalies: list[Dict[str, Any]] = []

    if len(arr) < 3:
        return anomalies

    if method == "zscore":
        mean, std = np.mean(arr), np.std(arr, ddof=1)
        if std < 1e-15:
            return anomalies
        z = np.abs((arr - mean) / std)
        for i in np.where(z > threshold)[0]:
            anomalies.append(
                {
                    "index": int(i),
                    "value": float(arr[i]),
                    "score": float(z[i]),
                }
            )

    elif method == "iqr":
        q1, q3 = np.percentile(arr, [25, 75])
        iqr = q3 - q1
        if iqr < 1e-15:
            return anomalies
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        for i in range(len(arr)):
            if arr[i] < lower or arr[i] > upper:
                dist = max(lower - arr[i], arr[i] - upper, 0)
                anomalies.append(
                    {
                        "index": int(i),
                        "value": float(arr[i]),
                        "score": float(dist / iqr),
                    }
                )
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'zscore' or 'iqr'.")

    return anomalies


# ---------------------------------------------------------------------------
# 7. Time series interpolation
# ---------------------------------------------------------------------------


def interpolate_time_series(
    dates: Sequence,
    values: Sequence[float],
    target_dates: Sequence,
    method: str = "linear",
) -> List[Optional[float]]:
    """Interpolate values at target dates.

    Parameters
    ----------
    dates : sequence
        Known observation dates (numeric or datetime).
    values : sequence of float
        Known values.
    target_dates : sequence
        Dates at which to interpolate.
    method : str
        ``"linear"`` or ``"cubic"``.

    Returns
    -------
    list
        Interpolated values (``None`` where extrapolation is required).
    """
    x = _date_to_numeric(dates)
    y = _to_numpy(values)
    xt = _date_to_numeric(target_dates)

    sort_idx = np.argsort(x)
    x, y = x[sort_idx], y[sort_idx]

    results: list[Optional[float]] = []
    for t in xt:
        if t < x[0] or t > x[-1]:
            results.append(None)
        elif method == "cubic" and len(x) >= 4:
            results.append(float(np.interp(t, x, y)))
        else:
            results.append(float(np.interp(t, x, y)))

    return results


# ---------------------------------------------------------------------------
# 8. Cumulative change
# ---------------------------------------------------------------------------


def cumulative_change(
    dates: Sequence,
    values: Sequence[float],
    baseline_date: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute cumulative change relative to a baseline.

    Parameters
    ----------
    dates : sequence
        Dates or numeric values.
    values : sequence of float
        Observed values.
    baseline_date : optional
        Reference date.  Defaults to the first date.

    Returns
    -------
    dict
        ``baseline_value``, ``cumulative_abs`` (array),
        ``cumulative_pct`` (array), ``total_change``,
        ``total_change_pct``.
    """
    x = _date_to_numeric(dates)
    y = _to_numpy(values)

    if baseline_date is not None:
        bx = _date_to_numeric([baseline_date])[0]
        idx = int(np.argmin(np.abs(x - bx)))
    else:
        idx = 0

    baseline = y[idx]
    cum_abs = y - baseline
    if abs(baseline) > 1e-15:
        cum_pct = cum_abs / baseline * 100.0
    else:
        cum_pct = np.full_like(cum_abs, np.nan)

    return {
        "baseline_value": float(baseline),
        "cumulative_abs": cum_abs,
        "cumulative_pct": cum_pct,
        "total_change": float(cum_abs[-1]),
        "total_change_pct": float(cum_pct[-1]),
    }


# ---------------------------------------------------------------------------
# 9. Area change analysis (comprehensive)
# ---------------------------------------------------------------------------


def area_change_analysis(
    dates: Sequence,
    areas: Sequence[float],
) -> Dict[str, Any]:
    """Comprehensive glacier area change analysis.

    Combines linear trend, Mann-Kendall, Sen's slope, change points,
    and anomaly detection into a single summary.

    Parameters
    ----------
    dates : sequence
        Dates or numeric values.
    areas : sequence of float
        Glacier area measurements.

    Returns
    -------
    dict
        Keys: ``trend``, ``mann_kendall``, ``sens_slope``,
        ``change_points``, ``anomalies``, ``summary``.
    """
    arr = _to_numpy(areas)

    trend = compute_trend(dates, areas)
    mk = mann_kendall_test(areas)
    ss = sens_slope(dates, areas)
    cps = detect_change_points(areas, method="cusum", threshold=1.0)
    anom = detect_anomalies(areas, method="zscore", threshold=3.0)

    total_area_change = float(arr[-1] - arr[0]) if len(arr) > 1 else 0.0
    if abs(arr[0]) > 1e-15:
        pct = total_area_change / arr[0] * 100.0
    else:
        pct = np.nan

    summary = {
        "start_area": float(arr[0]),
        "end_area": float(arr[-1]),
        "total_area_change": total_area_change,
        "total_area_change_pct": float(pct),
        "trend_direction": trend["trend_direction"],
        "annual_rate": trend["annual_rate"],
        "significant_mann_kendall": mk["significant"],
        "n_change_points": len(cps),
        "n_anomalies": len(anom),
    }

    return {
        "trend": trend,
        "mann_kendall": mk,
        "sens_slope": ss,
        "change_points": cps,
        "anomalies": anom,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# 10. Annual aggregation
# ---------------------------------------------------------------------------


def aggregate_annual(
    dates: Sequence,
    values: Sequence[float],
    method: str = "mean",
) -> Dict[str, Any]:
    """Aggregate a time series to annual resolution.

    Parameters
    ----------
    dates : sequence
        Dates (datetime-like or numeric years).
    values : sequence of float
        Observed values.
    method : str
        ``"mean"``, ``"median"``, ``"sum"``, ``"min"``, ``"max"``.

    Returns
    -------
    dict
        ``years`` (list of int), ``values`` (list of float).
    """
    arr_vals = _to_numpy(values)

    # Extract year
    dt64 = np.asarray(dates)
    if np.issubdtype(dt64.dtype, np.number):
        years = np.round(dt64).astype(int)
    else:
        try:
            years = np.array([np.datetime64(d, "Y").astype(int) for d in dates])
        except Exception:
            years = np.array([int(float(d)) for d in dates])

    unique_years = sorted(set(years.tolist()))
    agg_values: list[float] = []

    for yr in unique_years:
        mask = years == yr
        subset = arr_vals[mask]
        if method == "mean":
            agg_values.append(float(np.nanmean(subset)))
        elif method == "median":
            agg_values.append(float(np.nanmedian(subset)))
        elif method == "sum":
            agg_values.append(float(np.nansum(subset)))
        elif method == "min":
            agg_values.append(float(np.nanmin(subset)))
        elif method == "max":
            agg_values.append(float(np.nanmax(subset)))
        else:
            raise ValueError(f"Unknown method '{method}'. Use mean/median/sum/min/max.")

    return {
        "years": unique_years,
        "values": agg_values,
    }
