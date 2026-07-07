"""
Сквозной тест пайплайна на СИНТЕТИЧЕСКИХ данных.

Назначение: проверить, что src/config.py, src/preprocessing.py,
src/metrics.py и src/visualization.py работают вместе корректно ДО
появления реальных снимков Sentinel-2 (которые скачиваются через GEE
локально, см. 01_data_download.ipynb).

U-Net (src/models.py, требует tensorflow) проверяется отдельно
в _unet_smoke_test.py, т.к. tensorflow — тяжёлая зависимость.

Запуск: python3 _synthetic_smoke_test.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np

from src import config, metrics, preprocessing, visualization


def make_synthetic_scene(h=512, w=512, seed=0):
    """Синтетический "снимок" (H, W, N_CHANNELS) + бинарная маска ледника.

    Имитирует пятно "льда" (высокий NDSI, низкий BSI) на фоне "скалы/почвы".
    """
    rng = np.random.default_rng(seed)

    image = rng.uniform(0.05, 0.3, size=(h, w, config.N_CHANNELS)).astype(np.float32)

    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx, r = h * 0.6, w * 0.4, min(h, w) * 0.22
    glacier = ((yy - cy) ** 2 + (xx - cx) ** 2) <= r ** 2

    # На "льду" повышаем зелёный (B3) и снижаем SWIR (B11) -> высокий NDSI
    image[..., config.BAND_INDEX["B3"]] = np.where(glacier, 0.6, image[..., config.BAND_INDEX["B3"]])
    image[..., config.BAND_INDEX["B11"]] = np.where(glacier, 0.05, image[..., config.BAND_INDEX["B11"]])

    b3 = image[..., config.BAND_INDEX["B3"]]
    b11 = image[..., config.BAND_INDEX["B11"]]
    b8 = image[..., config.BAND_INDEX["B8"]]
    b4 = image[..., config.BAND_INDEX["B4"]]
    b2 = image[..., config.BAND_INDEX["B2"]]

    image[..., config.BAND_INDEX["NDSI"]] = (b3 - b11) / (b3 + b11 + 1e-8)
    image[..., config.BAND_INDEX["NDWI"]] = (b8 - b11) / (b8 + b11 + 1e-8)
    image[..., config.BAND_INDEX["BSI"]] = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + 1e-8)
    image[..., config.BAND_INDEX["EVI"]] = 2.5 * (b8 - b4) / (b8 + 6 * b4 - 7.5 * b2 + 1 + 1e-8)

    mask = glacier.astype(np.uint8)
    return image, mask


def main():
    print("== Тест 1: config ==")
    print("ALL_BAND_NAMES:", config.ALL_BAND_NAMES)
    print("N_CHANNELS:", config.N_CHANNELS)
    assert config.N_CHANNELS == 11
    assert config.BAND_INDEX["NDSI"] == 7

    print("\n== Тест 2: синтетическая сцена ==")
    image, mask = make_synthetic_scene()
    print("image:", image.shape, "mask:", mask.shape, "glacier frac:", mask.mean())
    assert image.shape == (512, 512, config.N_CHANNELS)
    assert 0 < mask.mean() < 1

    print("\n== Тест 3: create_patches / build_dataset ==")
    image2, mask2 = make_synthetic_scene(seed=1)
    X, y = preprocessing.build_dataset([(image, mask), (image2, mask2)])
    print("X:", X.shape, "y:", y.shape, "glacier frac in patches:", y.mean())
    assert X.shape[1:] == (config.PATCH_SIZE, config.PATCH_SIZE, config.N_CHANNELS)
    assert X.shape[0] == y.shape[0] > 0

    print("\n== Тест 4: augment_patch ==")
    aug_img, aug_mask = preprocessing.augment_patch(X[0], y[0])
    assert aug_img.shape == X[0].shape
    assert aug_mask.shape == y[0].shape

    print("\n== Тест 5: train_val_test_split ==")
    X_train, X_val, X_test, y_train, y_val, y_test = preprocessing.train_val_test_split(X, y)
    n = X.shape[0]
    print(f"train={len(X_train)} val={len(X_val)} test={len(X_test)} (total={n})")
    assert len(X_train) + len(X_val) + len(X_test) == n

    print("\n== Тест 6: NDSI baseline через metrics.evaluate_segmentation ==")
    ndsi_vals = X_test[..., config.BAND_INDEX["NDSI"]]
    y_pred_ndsi = (ndsi_vals > config.BEST_NDSI_THRESHOLD).astype(int)
    m = metrics.evaluate_segmentation(y_test, y_pred_ndsi)
    print({k: round(v, 3) for k, v in m.items()})
    assert m["f1"] > 0.5, "NDSI baseline должен разумно отделять синтетический лёд"

    print("\n== Тест 7: trend_analysis / forecast_to_2050 ==")
    years = np.array([2015, 2018, 2021, 2024])
    areas = np.array([100.0, 95.0, 91.0, 86.0])
    trend = metrics.trend_analysis(years, areas)
    print(trend)
    assert trend["slope_km2_per_year"] < 0
    assert trend["significant"]

    future_years, predicted, ci_lower, ci_upper, _ = metrics.forecast_to_2050(years, areas)
    print(f"2050 прогноз: {predicted[-1]:.1f} км² (CI {ci_lower[-1]:.1f}-{ci_upper[-1]:.1f})")
    assert future_years[-1] == 2050
    assert ci_lower[-1] < predicted[-1] < ci_upper[-1]

    print("\n== Тест 8: water supply estimate ==")
    wi = metrics.ice_volume_loss_to_water_supply(area_loss_km2=abs(trend["change_km2"]))
    print(wi)
    assert wi["days_of_supply_equivalent"] > 0

    print("\n== Тест 9: визуализация (без вывода на экран) ==")
    import matplotlib
    matplotlib.use("Agg")
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    visualization.plot_trend_forecast(
        years, areas, future_years, predicted, ci_lower, ci_upper,
        title="ТЕСТ: синтетический прогноз",
        save_path=config.FIGURES_DIR / "_smoke_test_forecast.png",
    )
    print("Сохранено:", config.FIGURES_DIR / "_smoke_test_forecast.png")

    print("\nВСЕ ТЕСТЫ ПРОЙДЕНЫ ✓")


if __name__ == "__main__":
    main()
