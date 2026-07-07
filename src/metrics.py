"""
Метрики качества сегментации, перевод площади из пикселей в км²,
статистика временного ряда и прогноз до 2050 года.
"""

from __future__ import annotations

import numpy as np

# ----------------------------------------------------------------------
# КЛАССИФИКАЦИОННЫЕ МЕТРИКИ
# ----------------------------------------------------------------------


def evaluate_segmentation(y_true, y_pred):
    """F1, Precision, Recall, IoU для бинарной сегментации.

    y_true, y_pred — массивы любой формы (сравниваются после flatten()),
    значения 0/1.
    """
    from sklearn.metrics import f1_score, jaccard_score, precision_score, recall_score

    y_true_f = np.asarray(y_true).flatten()
    y_pred_f = np.asarray(y_pred).flatten()

    return {
        "f1": f1_score(y_true_f, y_pred_f, zero_division=0),
        "precision": precision_score(y_true_f, y_pred_f, zero_division=0),
        "recall": recall_score(y_true_f, y_pred_f, zero_division=0),
        "iou": jaccard_score(y_true_f, y_pred_f, zero_division=0),
    }


# ----------------------------------------------------------------------
# ПЛОЩАДЬ ЛЕДНИКА
# ----------------------------------------------------------------------


def pixels_to_area_km2(n_pixels: int, pixel_area_m2: float) -> float:
    """Переводит количество пикселей в площадь в км²."""
    return n_pixels * pixel_area_m2 / 1e6


# ----------------------------------------------------------------------
# ВРЕМЕННОЙ РЯД: ТРЕНД И ПРОГНОЗ
# ----------------------------------------------------------------------


def trend_analysis(years, areas):
    """Линейная регрессия площадь(год) -> словарь со статистикой.

    Включает slope (км²/год), R², p-value, относительное изменение (%).
    """
    from scipy import stats

    years = np.asarray(years, dtype=float)
    areas = np.asarray(areas, dtype=float)

    slope, intercept, r_value, p_value, std_err = stats.linregress(years, areas)

    change_km2 = areas[-1] - areas[0]
    change_percent = change_km2 / areas[0] * 100 if areas[0] != 0 else np.nan

    return {
        "slope_km2_per_year": slope,
        "intercept": intercept,
        "r_squared": r_value**2,
        "p_value": p_value,
        "std_err": std_err,
        "significant": bool(p_value < 0.05),
        "change_km2": change_km2,
        "change_percent": change_percent,
    }


def forecast_to_2050(years, areas, target_year=2050):
    """Прогноз площади до target_year с 95% доверительным интервалом.

    Возвращает (future_years, predicted, ci_lower, ci_upper, trend_dict).
    """
    from scipy import stats

    years = np.asarray(years, dtype=float)
    areas = np.asarray(areas, dtype=float)

    slope, intercept, r_value, p_value, std_err = stats.linregress(years, areas)
    trend = trend_analysis(years, areas)

    future_years = np.arange(years[-1], target_year + 1)
    predicted = slope * future_years + intercept

    se = std_err * np.sqrt(
        1 + 1 / len(years) + (future_years - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum()
    )
    ci_upper = predicted + 1.96 * se
    ci_lower = predicted - 1.96 * se

    return future_years, predicted, ci_lower, ci_upper, trend


# ----------------------------------------------------------------------
# PER-GLACIER INSTANCE METRICS (P4.1)
# ----------------------------------------------------------------------


def per_glacier_metrics(y_true, y_pred, glacier_polygons, transform=None):
    """Per-polygon F1/IoU for each glacier instance.

    Parameters
    ----------
    y_true : np.ndarray (H, W)  binary ground-truth mask
    y_pred : np.ndarray (H, W)  binary prediction mask
    glacier_polygons : list of shapely Polygon objects
        One polygon per glacier instance.
    transform : rasterio.Affine | None
        If given, geometries are in CRS coordinates; pixels are extracted
        via rasterio.features.geometry_mask.  If None, geometries must
        already be boolean (H, W) arrays.

    Returns
    -------
    dict with per-glacier results and summary statistics.
    """
    from sklearn.metrics import f1_score, jaccard_score, precision_score, recall_score

    y_true_arr = np.asarray(y_true, dtype=np.uint8)
    y_pred_arr = np.asarray(y_pred, dtype=np.uint8)
    h, w = y_true_arr.shape

    per_glacier = []
    for idx, poly in enumerate(glacier_polygons):
        if hasattr(poly, "astype"):
            roi = poly.astype(bool)
        elif transform is not None:
            try:
                import rasterio.features

                roi = ~rasterio.features.geometry_mask([poly], out_shape=(h, w), transform=transform)
            except Exception:
                roi = np.zeros((h, w), dtype=bool)
        else:
            roi = np.zeros((h, w), dtype=bool)

        yt = y_true_arr[roi].flatten()
        yp = y_pred_arr[roi].flatten()
        if len(yt) == 0 or yt.sum() == 0:
            continue

        per_glacier.append(
            {
                "glacier_idx": idx,
                "f1": float(f1_score(yt, yp, zero_division=0)),
                "iou": float(jaccard_score(yt, yp, zero_division=0)),
                "precision": float(precision_score(yt, yp, zero_division=0)),
                "recall": float(recall_score(yt, yp, zero_division=0)),
                "pixel_count": int(roi.sum()),
            }
        )

    if not per_glacier:
        return {"per_glacier": [], "mean_f1": 0.0, "mean_iou": 0.0, "std_f1": 0.0, "std_iou": 0.0}

    f1s = np.array([g["f1"] for g in per_glacier])
    ious = np.array([g["iou"] for g in per_glacier])
    return {
        "per_glacier": per_glacier,
        "mean_f1": float(f1s.mean()),
        "std_f1": float(f1s.std()),
        "mean_iou": float(ious.mean()),
        "std_iou": float(ious.std()),
    }


# ----------------------------------------------------------------------
# AUC-ROC AND CONFUSION MATRIX (P4.2)
# ----------------------------------------------------------------------


def evaluate_segmentation_roc(y_true, y_pred_proba, threshold: float = 0.5):
    """AUC-ROC, precision-recall curve, confusion matrix for binary segmentation.

    Parameters
    ----------
    y_true : array-like  binary ground-truth (0/1)
    y_pred_proba : array-like  continuous predictions in [0, 1]
    threshold : float  binarisation threshold for confusion matrix

    Returns
    -------
    dict with roc_auc, pr_auc, confusion_matrix, and optimal threshold.
    """
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        roc_auc_score,
        roc_curve,
    )

    yt = np.asarray(y_true).flatten()
    yp = np.asarray(y_pred_proba).flatten()
    yb = (yp >= threshold).astype(np.uint8)

    roc_auc = float(roc_auc_score(yt, yp))
    pr_auc = float(average_precision_score(yt, yp))

    fpr, tpr, thresholds = roc_curve(yt, yp)
    j_scores = tpr - fpr
    optimal_idx = int(np.argmax(j_scores))
    optimal_threshold = float(thresholds[optimal_idx])

    cm = confusion_matrix(yt, yb)
    tn, fp, fn, tp = cm.ravel().tolist()

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "optimal_threshold": optimal_threshold,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "roc_curve": {
            "fpr": fpr.tolist()[:100],
            "tpr": tpr.tolist()[:100],
        },
    }


# ----------------------------------------------------------------------
# WGMS-ВАЛИДАЦИЯ (Идея A исследовательской базы)
# ----------------------------------------------------------------------


def rmse_against_wgms(predicted_areas: dict, wgms_areas: dict):
    """Сравнивает предсказанные площади с независимыми данными WGMS.

    predicted_areas, wgms_areas : dict[int year -> float area_km2]
        Используются только годы, присутствующие в обоих словарях.

    Возвращает (rmse, common_years, diffs_dict).
    """
    common_years = sorted(set(predicted_areas) & set(wgms_areas))
    if not common_years:
        raise ValueError("Нет общих лет между предсказаниями и данными WGMS.")

    diffs = {y: predicted_areas[y] - wgms_areas[y] for y in common_years}
    rmse = float(np.sqrt(np.mean([d**2 for d in diffs.values()])))
    return rmse, common_years, diffs


# ----------------------------------------------------------------------
# ВОДНЫЙ БАЛАНС АЛМАТЫ (Идея C исследовательской базы)
# ----------------------------------------------------------------------


def ice_volume_loss_to_water_supply(
    area_loss_km2: float,
    mean_ice_thickness_m: float = 30.0,
    population: int = 2_400_000,
    per_capita_liters_per_day: float = 400.0,
):
    """Грубая оценка: сколько дней водопотребления Алматы покрывает
    потерянный объём льда.

    1 км² * толщина(м) -> объём льда (м³) -> вода (м³, ice->water density 0.9)
    -> литры -> дни потребления города.

    Это ОЦЕНОЧНЫЙ расчёт для иллюстрации масштаба проблемы (killer-fact),
    а не гидрологическая модель.
    """
    ice_density_to_water = 0.9
    volume_ice_m3 = area_loss_km2 * 1e6 * mean_ice_thickness_m
    volume_water_m3 = volume_ice_m3 * ice_density_to_water
    volume_water_liters = volume_water_m3 * 1000

    city_daily_demand_liters = population * per_capita_liters_per_day
    days_of_supply = volume_water_liters / city_daily_demand_liters

    return {
        "volume_water_m3": volume_water_m3,
        "city_daily_demand_liters": city_daily_demand_liters,
        "days_of_supply_equivalent": days_of_supply,
        "years_of_supply_equivalent": days_of_supply / 365.25,
    }
