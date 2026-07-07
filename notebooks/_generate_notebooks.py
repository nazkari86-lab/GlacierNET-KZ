"""
Генератор Jupyter-ноутбуков проекта GlacierNET-KZ.

Запуск: python3 _generate_notebooks.py
Создаёт/перезаписывает 01..06 *.ipynb в этой папке.
Хранить исходники ноутбуков как код (этот файл) удобнее для ревью в git,
чем редактировать .ipynb JSON напрямую.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def nb(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (glaciers)",
                "language": "python",
                "name": "glaciers",
            },
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


# ======================================================================
# 01 — СКАЧИВАНИЕ ДАННЫХ
# ======================================================================

cells_01 = [
    md("""# 01 — Скачивание данных (Sentinel-2, Landsat, RGI)

**Требует:** аутентификации Google Earth Engine (`earthengine authenticate` в терминале)
и доступа к интернету. Этот ноутбук НЕ выполняется в облачной песочнице —
запускайте его локально (Anaconda + `conda activate glaciers`).

Результат: GeoTIFF-композиты в `data/raw/sentinel2/` и `data/raw/landsat/`
(после скачивания вручную из Google Drive, папка `GlacierKZ`),
а также контуры RGI в `data/rgi/`.
"""),
    code("""import sys
sys.path.append('..')

import ee
import geemap
import os

from src import config, data_loader

ee.Initialize()
print(ee.String('Earth Engine работает!').getInfo())
"""),
    md("""## Область исследования

Используем `config.STUDY_AREA_BBOX` — Заилийский Алатау, бассейн рек
Малая/Большая Алматинка (ледники Туюксу, Богдановича и др.).
"""),
    code("""STUDY_AREA = ee.Geometry.BBox(*config.STUDY_AREA_BBOX)

m = geemap.Map()
m.centerObject(STUDY_AREA, 10)
m.addLayer(STUDY_AREA, {}, 'Study area')
m
"""),
    md("## Sentinel-2 (2015–2024)"),
    code("""os.makedirs(config.DATA_RAW_SENTINEL2, exist_ok=True)

for year in config.YEARS_SENTINEL2:
    print(f"\\n--- Обрабатываем {year} ---")
    img = data_loader.get_sentinel2(year, STUDY_AREA)
    if img is not None:
        print(f"  Каналы: {img.bandNames().getInfo()}")
        data_loader.export_year_to_drive(img, year, STUDY_AREA, prefix='sentinel2')
    else:
        print(f"  Нет данных за {year}, пропускаем")

print("\\nВсе задачи запущены! Проверь прогресс на code.earthengine.google.com/tasks")
print("После завершения — скачай файлы из Google Drive (папка GlacierKZ) в data/raw/sentinel2/")
print("Индексы NDSI/NDWI/BSI/EVI будут добавлены локально в data_loader.load_image().")
"""),
    md("## Landsat (2000–2013)"),
    code("""os.makedirs(config.DATA_RAW_LANDSAT, exist_ok=True)

for year in config.YEARS_LANDSAT:
    print(f"\\n--- Обрабатываем {year} (Landsat) ---")
    img = data_loader.get_landsat(year, STUDY_AREA)
    if img is not None:
        img = data_loader.add_indices(img)
        data_loader.export_year_to_drive(img, year, STUDY_AREA, prefix='landsat')
    else:
        print(f"  Нет данных за {year}, пропускаем")

print("\\nЗадачи Landsat запущены. Скачай результаты в data/raw/landsat/")
"""),
    md("""## RGI 7.0 — контуры ледников

Скачай регион 13 (Central Asia) с https://www.glims.org/RGI/rgi70_dl.html
(или через `ee.FeatureCollection('GLIMS/current')`), сохрани shapefile в `data/rgi/`.
"""),
    code("""# Вариант: контуры ледников прямо из Earth Engine (GLIMS)
rgi_fc = ee.FeatureCollection('GLIMS/current')
kz_glaciers = rgi_fc.filterBounds(STUDY_AREA)
print('Ледников в области исследования:', kz_glaciers.size().getInfo())

# Экспорт в Drive как shapefile/GeoJSON для дальнейшей работы в geopandas/QGIS
task = ee.batch.Export.table.toDrive(
    collection=kz_glaciers,
    description='rgi_study_area',
    folder='GlacierKZ',
    fileNamePrefix='rgi_study_area',
    fileFormat='SHP',
)
task.start()
print('Экспорт контуров RGI запущен -> data/rgi/rgi_study_area.shp')
"""),
    md("""## Чек-лист после выполнения

- [ ] Sentinel-2 за минимум 5 лет (2015–2024) скачаны в `data/raw/sentinel2/`
- [ ] Landsat за 2000–2013 скачаны в `data/raw/landsat/`
- [ ] RGI контуры в `data/rgi/`
- [ ] Все файлы открываются в QGIS без ошибок (Layer -> Add Raster/Vector Layer)
"""),
]


# ======================================================================
# 02 — ПРЕДОБРАБОТКА
# ======================================================================

cells_02 = [
    md("""# 02 — Предобработка: маски, патчи, train/val/test

Требует наличия скачанных снимков (`data/raw/sentinel2/sentinel2_<year>.tif`)
и контуров RGI (`data/rgi/`). Если данных пока нет — см. `_synthetic_smoke_test.py`
для проверки пайплайна на синтетических данных.
"""),
    code("""import sys
sys.path.append('..')

import numpy as np
import geopandas as gpd
from pathlib import Path
from tqdm import tqdm
import matplotlib.pyplot as plt

from src import config, data_loader, preprocessing
"""),
    md("## 2.1 Растеризация контуров RGI в маски"),
    code("""rgi_path = config.DATA_RGI / 'rgi_study_area.shp'
rgi = gpd.read_file(rgi_path)
print(f"Контуров ледников в области: {len(rgi)}")

config.DATA_MASKS.mkdir(parents=True, exist_ok=True)

# Для лет 2020-2024 используем RGI как есть (свежие контуры),
# для более старых лет см. README про ручную корректировку в QGIS.
for year in [2020, 2021, 2022, 2023, 2024]:
    ref_path = config.DATA_RAW_SENTINEL2 / f'sentinel2_{year}.tif'
    if not ref_path.exists():
        print(f'  {year}: нет снимка, пропуск')
        continue
    out_path = config.DATA_MASKS / f'mask_{year}.tif'
    mask = preprocessing.rasterize_rgi_to_mask(rgi, ref_path, out_path)
    print(f'  {year}: маска сохранена, пикселей ледника = {mask.sum()}')
"""),
    md("## 2.2 Загрузка снимков и масок, EDA"),
    code("""sentinel_files = sorted(config.DATA_RAW_SENTINEL2.glob('sentinel2_20*.tif'))
print(f'Найдено снимков: {len(sentinel_files)}')

# Пример: посмотреть один снимок и его маску
example_year = 2024
img = data_loader.load_image(config.DATA_RAW_SENTINEL2 / f'sentinel2_{example_year}.tif')
mask = data_loader.load_mask(config.DATA_MASKS / f'mask_{example_year}.tif')

print('Снимок:', img.shape, 'Маска:', mask.shape)
print(f'Доля пикселей ледника: {mask.mean():.2%}')

from src import visualization
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
visualization.show_rgb(img, ax=axes[0], title=f'Sentinel-2 {example_year} (RGB)')
visualization.show_mask(mask, ax=axes[1], title='RGI маска ледников')
plt.tight_layout()
plt.savefig(config.FIGURES_DIR / 'eda_example.png', dpi=150)
plt.show()
"""),
    md("## 2.3 Нарезка на патчи и сборка датасета"),
    code("""pairs = []
for img_file in tqdm(sentinel_files):
    year = img_file.stem.split('_')[1]
    mask_file = config.DATA_MASKS / f'mask_{year}.tif'
    if not mask_file.exists():
        print(f'Нет маски для {year}, пропускаем')
        continue

    image = data_loader.load_image(img_file)
    mask = data_loader.load_mask(mask_file)
    pairs.append((image, mask))
    print(f'  {year}: снимок {image.shape}, ледник {mask.mean():.2%}')

X, y = preprocessing.build_dataset(pairs)
print(f'\\nИтого патчей: {X.shape[0]}')
print(f'Форма патча: {X.shape[1:]}')
print(f'Баланс классов: {y.mean():.2%} пикселей — ледник')
"""),
    md("## 2.4 Разделение train/val/test и сохранение"),
    code("""X_train, X_val, X_test, y_train, y_val, y_test = preprocessing.train_val_test_split(X, y)

print(f'Обучение:  {X_train.shape[0]} патчей')
print(f'Валидация: {X_val.shape[0]} патчей')
print(f'Тест:      {X_test.shape[0]} патчей')

config.DATA_PATCHES.mkdir(parents=True, exist_ok=True)
np.save(config.DATA_PATCHES / 'X_train.npy', X_train)
np.save(config.DATA_PATCHES / 'X_val.npy',   X_val)
np.save(config.DATA_PATCHES / 'X_test.npy',  X_test)
np.save(config.DATA_PATCHES / 'y_train.npy', y_train)
np.save(config.DATA_PATCHES / 'y_val.npy',   y_val)
np.save(config.DATA_PATCHES / 'y_test.npy',  y_test)

print('\\nДанные сохранены в data/processed/patches/')
"""),
]


# ======================================================================
# 03 — БАЗОВЫЕ МОДЕЛИ
# ======================================================================

cells_03 = [
    md("""# 03 — Базовые модели: NDSI и Random Forest

Контрольный эксперимент: сравнение с базовыми моделями доказывает
научную ценность U-Net (Месяц 4 плана).
"""),
    code("""import sys
sys.path.append('..')

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

from src import config, metrics

X_train = np.load(config.DATA_PATCHES / 'X_train.npy')
X_test  = np.load(config.DATA_PATCHES / 'X_test.npy')
y_train = np.load(config.DATA_PATCHES / 'y_train.npy')
y_test  = np.load(config.DATA_PATCHES / 'y_test.npy')

print('N каналов:', X_train.shape[-1], '(ожидается', config.N_CHANNELS, ')')
"""),
    code("""def flatten_for_ml(X, y):
    N, H, W, C = X.shape
    return X.reshape(N * H * W, C), y.reshape(N * H * W)

X_train_flat, y_train_flat = flatten_for_ml(X_train, y_train)
X_test_flat,  y_test_flat  = flatten_for_ml(X_test, y_test)

print(f'Обучающих пикселей: {X_train_flat.shape[0]:,}')
"""),
    md("""## Модель 1: NDSI пороговая классификация

Индекс NDSI берётся по `config.BAND_INDEX['NDSI']` — это устраняет
ошибку из черновика плана с "магическим" индексом 7.
"""),
    code("""NDSI_INDEX = config.BAND_INDEX['NDSI']
results_rows = []

for threshold in config.NDSI_THRESHOLDS:
    ndsi_vals = X_test_flat[:, NDSI_INDEX]
    y_pred_ndsi = (ndsi_vals > threshold).astype(int)
    m = metrics.evaluate_segmentation(y_test_flat, y_pred_ndsi)
    print(f"NDSI > {threshold}: F1={m['f1']:.3f}, Precision={m['precision']:.3f}, "
          f"Recall={m['recall']:.3f}, IoU={m['iou']:.3f}")
    results_rows.append({'threshold': threshold, **m})

best_row = max(results_rows, key=lambda r: r['f1'])
BEST_NDSI_THRESHOLD = best_row['threshold']
print(f'\\nЛучший порог NDSI: {BEST_NDSI_THRESHOLD} (F1={best_row["f1"]:.3f})')

y_pred_ndsi_best = (X_test_flat[:, NDSI_INDEX] > BEST_NDSI_THRESHOLD).astype(int)
ndsi_metrics = metrics.evaluate_segmentation(y_test_flat, y_pred_ndsi_best)
"""),
    md("## Модель 2: Случайный лес"),
    code("""np.random.seed(config.RANDOM_SEED)
n_sample = min(1_000_000, len(X_train_flat))
idx = np.random.choice(len(X_train_flat), n_sample, replace=False)

rf = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    class_weight='balanced',
    n_jobs=-1,
    random_state=config.RANDOM_SEED,
)

print('Обучение случайного леса...')
rf.fit(X_train_flat[idx], y_train_flat[idx])
print('Случайный лес обучен!')

y_pred_rf = rf.predict(X_test_flat)
rf_metrics = metrics.evaluate_segmentation(y_test_flat, y_pred_rf)
print(f"Случайный лес: F1={rf_metrics['f1']:.3f}, Precision={rf_metrics['precision']:.3f}, "
      f"Recall={rf_metrics['recall']:.3f}, IoU={rf_metrics['iou']:.3f}")

feature_importance = sorted(zip(config.ALL_BAND_NAMES, rf.feature_importances_), key=lambda x: -x[1])
for name, imp in feature_importance:
    print(f'  {name}: {imp:.3f}')

config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(rf, config.MODELS_DIR / 'random_forest.pkl')
"""),
    md("## Сводная таблица (заполнится U-Net в ноутбуке 04)"),
    code("""results = {
    'Метод': ['NDSI (порог)', 'Случайный лес'],
    'F1-score':  [ndsi_metrics['f1'], rf_metrics['f1']],
    'Precision': [ndsi_metrics['precision'], rf_metrics['precision']],
    'Recall':    [ndsi_metrics['recall'], rf_metrics['recall']],
    'IoU':       [ndsi_metrics['iou'], rf_metrics['iou']],
}

df_results = pd.DataFrame(results)
print(df_results.to_string(index=False))

config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
df_results.to_csv(config.TABLES_DIR / 'model_comparison.csv', index=False)
"""),
]


# ======================================================================
# 04 — U-NET
# ======================================================================

cells_04 = [
    md("""# 04 — Обучение U-Net

Главная модель проекта. Архитектура и функции потерь — в `src/models.py`.
"""),
    code("""import sys
sys.path.append('..')

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import callbacks

from src import config, models, visualization, metrics

print('GPU доступен:', tf.config.list_physical_devices('GPU'))
# Если нет GPU — обучение займёт 2-6 часов на CPU. Это нормально.
"""),
    code("""X_train = np.load(config.DATA_PATCHES / 'X_train.npy').astype(np.float32)
X_val   = np.load(config.DATA_PATCHES / 'X_val.npy').astype(np.float32)
X_test  = np.load(config.DATA_PATCHES / 'X_test.npy').astype(np.float32)
y_train = np.load(config.DATA_PATCHES / 'y_train.npy')
y_val   = np.load(config.DATA_PATCHES / 'y_val.npy')
y_test  = np.load(config.DATA_PATCHES / 'y_test.npy')

N_CHANNELS = X_train.shape[-1]
unet = models.build_unet(input_shape=(config.PATCH_SIZE, config.PATCH_SIZE, N_CHANNELS))
unet = models.compile_model(unet)
unet.summary()
"""),
    code("""GlacierDataGenerator = models.build_data_generator()

train_gen = GlacierDataGenerator(X_train, y_train, batch_size=config.BATCH_SIZE, augment=True)
val_gen   = GlacierDataGenerator(X_val,   y_val,   batch_size=config.BATCH_SIZE, augment=False)

config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

cbs = [
    callbacks.ModelCheckpoint(
        str(config.MODELS_DIR / 'unet_best.h5'),
        save_best_only=True, monitor='val_dice_coefficient', mode='max', verbose=1,
    ),
    callbacks.EarlyStopping(
        patience=15, restore_best_weights=True, monitor='val_dice_coefficient', mode='max',
    ),
    callbacks.ReduceLROnPlateau(
        factor=0.5, patience=7, monitor='val_loss', min_lr=1e-6, verbose=1,
    ),
    callbacks.CSVLogger(str(config.RESULTS_DIR / 'training_log.csv')),
]
"""),
    code("""history = unet.fit(
    train_gen,
    validation_data=val_gen,
    epochs=config.EPOCHS,
    callbacks=cbs,
    verbose=1,
)
"""),
    code("""visualization.plot_training_curves(history, save_path=config.FIGURES_DIR / 'training_curves.png')
"""),
    md("## Оценка на тестовой выборке"),
    code("""y_pred_prob = unet.predict(X_test, batch_size=config.BATCH_SIZE)
y_pred = (y_pred_prob.squeeze() > 0.5).astype(int)

unet_metrics = metrics.evaluate_segmentation(y_test, y_pred)
print('U-Net результаты на тестовой выборке:')
for k, v in unet_metrics.items():
    print(f'  {k}: {v:.3f}')

visualization.plot_prediction_grid(X_test, y_test, y_pred, n_examples=4,
                                    save_path=config.FIGURES_DIR / 'predictions_examples.png')
"""),
    md("## Обновление сравнительной таблицы"),
    code("""df_results = pd.read_csv(config.TABLES_DIR / 'model_comparison.csv')
df_results = pd.concat([df_results, pd.DataFrame([{
    'Метод': 'U-Net (наш)',
    'F1-score': unet_metrics['f1'],
    'Precision': unet_metrics['precision'],
    'Recall': unet_metrics['recall'],
    'IoU': unet_metrics['iou'],
}])], ignore_index=True)

print(df_results.to_string(index=False))
df_results.to_csv(config.TABLES_DIR / 'model_comparison.csv', index=False)

visualization.plot_model_comparison(df_results, metric='F1-score',
                                     save_path=config.FIGURES_DIR / 'model_comparison_f1.png')
visualization.plot_model_comparison(df_results, metric='IoU',
                                     save_path=config.FIGURES_DIR / 'model_comparison_iou.png')
"""),
]


# ======================================================================
# 05 — ВРЕМЕННОЙ АНАЛИЗ
# ======================================================================

cells_05 = [
    md("""# 05 — Временной анализ, тренд и прогноз до 2050

Главный научный результат проекта.
"""),
    code("""import sys
sys.path.append('..')

import numpy as np
import pandas as pd
import tensorflow as tf
import rasterio

from src import config, data_loader, models, metrics, visualization

unet = tf.keras.models.load_model(
    config.MODELS_DIR / 'unet_best.h5',
    custom_objects=models.get_custom_objects(),
)
"""),
    md("## Применяем U-Net ко всем годам Sentinel-2"),
    code("""results = []
config.MASKS_PRED_DIR.mkdir(parents=True, exist_ok=True)

for year in config.YEARS_SENTINEL2:
    img_path = config.DATA_RAW_SENTINEL2 / f'sentinel2_{year}.tif'
    if not img_path.exists():
        print(f'{year}: снимок не найден, пропуск')
        continue

    print(f'Обрабатываем {year}...', end=' ')
    image = data_loader.load_image(img_path)
    prob_map, binary_mask = models.predict_full_image(image, unet)

    transform, crs, shape, pixel_area_m2 = data_loader.read_raster_meta(img_path)
    area_km2 = metrics.pixels_to_area_km2(binary_mask.sum(), pixel_area_m2)
    results.append({'year': year, 'area_km2': area_km2, 'source': 'Sentinel-2 (U-Net)'})
    print(f'Площадь: {area_km2:.2f} км²')

    with rasterio.open(
        config.MASKS_PRED_DIR / f'mask_pred_{year}.tif', 'w',
        driver='GTiff', height=shape[0], width=shape[1],
        count=1, dtype='uint8', crs=crs, transform=transform,
    ) as dst:
        dst.write(binary_mask, 1)

df = pd.DataFrame(results)
print('\\n=== РЕЗУЛЬТАТЫ ПО ГОДАМ ===')
print(df.to_string(index=False))
config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(config.TABLES_DIR / 'glacier_areas_by_year.csv', index=False)
"""),
    md("""## Landsat (2000–2013)

Для старых лет каналов B8A/B12 нет — модель U-Net (обученная на 11 каналах
Sentinel-2) неприменима напрямую. Используем NDSI-пороговый метод
(`config.BEST_NDSI_THRESHOLD`, из ноутбука 03) на доступных каналах
B2/B3/B4/B8/B11 как для Landsat-композитов.
"""),
    code("""landsat_results = []

for year in config.YEARS_LANDSAT:
    img_path = config.DATA_RAW_LANDSAT / f'landsat_{year}.tif'
    if not img_path.exists():
        print(f'{year}: снимок Landsat не найден, пропуск')
        continue

    image = data_loader.load_image(img_path)
    ndsi = image[:, :, config.BAND_INDEX['NDSI']]
    binary_mask = (ndsi > config.BEST_NDSI_THRESHOLD).astype('uint8')

    _, crs, _, pixel_area_m2 = data_loader.read_raster_meta(img_path)
    area_km2 = metrics.pixels_to_area_km2(binary_mask.sum(), pixel_area_m2)
    landsat_results.append({'year': year, 'area_km2': area_km2, 'source': 'Landsat (NDSI)'})
    print(f'{year}: площадь (NDSI) = {area_km2:.2f} км²')

df_landsat = pd.DataFrame(landsat_results)
df_all = pd.concat([df_landsat, df], ignore_index=True).sort_values('year')
print(df_all.to_string(index=False))
df_all.to_csv(config.TABLES_DIR / 'glacier_areas_all_years.csv', index=False)
"""),
    md("## Статистика тренда"),
    code("""years = df['year'].values
areas = df['area_km2'].values

trend = metrics.trend_analysis(years, areas)
print('Статистика (Sentinel-2 / U-Net период):')
print(f"  Тренд:   {trend['slope_km2_per_year']:.3f} км²/год")
print(f"  R²:      {trend['r_squared']:.3f}")
print(f"  p-value: {trend['p_value']:.4f} {'(значимо!)' if trend['significant'] else '(не значимо)'}")
print(f"  Изменение: {trend['change_km2']:.2f} км² ({trend['change_percent']:.1f}%)")
"""),
    md("## Прогноз до 2050"),
    code("""future_years, predicted, ci_lower, ci_upper, _ = metrics.forecast_to_2050(years, areas)

visualization.plot_trend_forecast(
    years, areas, future_years, predicted, ci_lower, ci_upper,
    title='Изменение площади ледников Заилийского Алатау: 2015–2050\\n(U-Net на снимках Sentinel-2)',
    save_path=config.FIGURES_DIR / 'glacier_trend_forecast.png',
)

area_2050 = predicted[-1]
print(f"Прогноз на 2050: {area_2050:.1f} км² "
      f"(95% CI: {ci_lower[-1]:.1f}-{ci_upper[-1]:.1f} км²)")
"""),
    md("""## WGMS-валидация (Туюксу)

Заполни словарь `wgms_areas_km2` реальными данными из
https://wgms.ch/products_ref_glaciers/tuyuksuyskiy/ (FoG Browser -> Download Data).
"""),
    code("""# Пример структуры (значения-плейсхолдеры -- замени реальными из WGMS!)
wgms_areas_km2 = {
    # 2018: 2.32,
    # 2020: 2.30,
    # 2022: 2.28,
}

predicted_areas_km2 = dict(zip(df['year'], df['area_km2']))

if wgms_areas_km2:
    rmse, common_years, diffs = metrics.rmse_against_wgms(predicted_areas_km2, wgms_areas_km2)
    print(f'RMSE против WGMS ({len(common_years)} лет): {rmse:.4f} км²')
    for y in common_years:
        print(f'  {y}: предсказано {predicted_areas_km2[y]:.3f}, WGMS {wgms_areas_km2[y]:.3f}, '
              f'разница {diffs[y]:+.3f}')
else:
    print('Заполни wgms_areas_km2 данными с wgms.ch для валидации.')
"""),
    md("## Водоснабжение Алматы (killer-fact)"),
    code("""area_loss = abs(trend['change_km2'])
water_impact = metrics.ice_volume_loss_to_water_supply(area_loss)

print(f"Потеря площади за период: {area_loss:.2f} км²")
print(f"Эквивалент в водоснабжении Алматы: "
      f"{water_impact['days_of_supply_equivalent']:.0f} дней "
      f"({water_impact['years_of_supply_equivalent']:.2f} года) потребления города")
"""),
]


# ======================================================================
# 06 — ВИЗУАЛИЗАЦИЯ
# ======================================================================

cells_06 = [
    md("""# 06 — Финальная визуализация и карты

Сборка итоговых рисунков для научной работы и презентации.
"""),
    code("""import sys
sys.path.append('..')

import pandas as pd
import matplotlib.pyplot as plt
import rasterio
from rasterio.plot import show

from src import config, data_loader, visualization
"""),
    md("## Карта изменения ледников (наложение масок по годам)"),
    code("""years_to_plot = [y for y in config.YEARS_SENTINEL2 if (config.MASKS_PRED_DIR / f'mask_pred_{y}.tif').exists()]

fig, axes = plt.subplots(1, len(years_to_plot), figsize=(5 * len(years_to_plot), 5))
if len(years_to_plot) == 1:
    axes = [axes]

for ax, year in zip(axes, years_to_plot):
    with rasterio.open(config.MASKS_PRED_DIR / f'mask_pred_{year}.tif') as src:
        mask = src.read(1)
    visualization.show_mask(mask, ax=ax, title=str(year))

plt.tight_layout()
plt.savefig(config.FIGURES_DIR / 'glacier_maps_by_year.png', dpi=150)
plt.show()
"""),
    md("## Сводная таблица методов и итоговый отчёт"),
    code("""df_results = pd.read_csv(config.TABLES_DIR / 'model_comparison.csv')
print(df_results.to_string(index=False))

df_areas = pd.read_csv(config.TABLES_DIR / 'glacier_areas_all_years.csv')
print(df_areas.to_string(index=False))
"""),
    md("""## Чек-лист готовых рисунков для научной работы

- `results/figures/eda_example.png` — пример снимка и маски
- `results/figures/training_curves.png` — кривые обучения U-Net
- `results/figures/predictions_examples.png` — примеры предсказаний
- `results/figures/model_comparison_f1.png`, `model_comparison_iou.png`
- `results/figures/glacier_trend_forecast.png` — главный график (тренд + прогноз)
- `results/figures/glacier_maps_by_year.png` — карты по годам
- `results/tables/model_comparison.csv`
- `results/tables/glacier_areas_all_years.csv`
"""),
]


NOTEBOOKS = {
    "01_data_download.ipynb": cells_01,
    "02_preprocessing.ipynb": cells_02,
    "03_baseline_models.ipynb": cells_03,
    "04_unet_training.ipynb": cells_04,
    "05_temporal_analysis.ipynb": cells_05,
    "06_visualization.ipynb": cells_06,
}


def main():
    for filename, cells in NOTEBOOKS.items():
        path = HERE / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(nb(cells), f, ensure_ascii=False, indent=1)
        print(f"Записано: {path}")


if __name__ == "__main__":
    main()
