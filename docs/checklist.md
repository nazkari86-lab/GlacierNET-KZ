# Контрольные точки проекта (из плана, Часть 4)

Статус обновлён 2026-06-28 после полной загрузки raw-данных и проверки качества.

## Месяц 1 — Окружение
- [x] Miniforge установлена, окружение `glaciers` создано
- [x] Все библиотеки установлены без ошибок (`requirements.txt`,
      geo-библиотеки через conda)
- [x] GEE аккаунт получен и `ee.Initialize()` работает
- [ ] VS Code настроен с правильным интерпретатором
- [x] Структура папок создана (этот репозиторий)
- [ ] Пройден базовый Python (numpy, pandas, matplotlib)
- [ ] Базовый QGIS освоен

## Месяц 2 — Данные
- [x] Ледники выбраны, координаты записаны (`src/config.py:GLACIERS`)
- [x] Данные Sentinel-2 скачаны (2015–2024; 2015 — late-year TOA fallback, 2020/2022 — compact exports)
- [x] Данные Landsat за 2000–2013 скачаны (2000, 2003, 2005, 2008, 2010, 2013)
- [x] RGI контуры загружены для изучаемого района
- [x] Официальные ancillary-источники зафиксированы и подготовлены:
      Copernicus DEM GLO-30 (высота, уклон, экспозиция), ESA WorldCover 2021
      (land-cover context), WGMS GlaThiDa (внешний thickness reference); полный
      checksummed каталог создается через `scripts/build_ml_dataset_catalog.py`
- [~] Sentinel-1 GRD summer composites 2017–2024 отправлены в Google Earth
      Engine/Drive и загружены с проверкой размера; SAR-каналы доступны как
      опциональные `VV/VH` признаки в `scripts/build_multimodal_patches.py`,
      но еще не смешаны с текущим 14-канальным benchmark
- [x] Маски ледников созданы для строгих Sentinel-2 лет 2016–2024
      (`data/processed/masks/mask_*.tif`,
      `data/processed/masks/manifest.json`)
- [x] Data quality gate пройден (`results/data_quality_report.json`, `ok=true`)
- [x] STAC/data inventory обновлены (`results/stac/catalog.json`, `results/tables/data_inventory.csv`)

## Месяц 3 — Предобработка
- [x] Нормализация данных реализована корректно (значения 0–1)
      (`src/data_loader.load_image`)
- [x] Спектральные индексы вычислены (NDSI, NDWI, BSI, EVI)
      (`src/data_loader.add_indices`, проверено в smoke-тесте)
- [x] Код нарезки патчей реализован и протестирован
      (`src/preprocessing.create_patches`, минимум 500 патчей —
      зависит от реальных данных)
- [x] Код разделения train/val/test реализован
      (`src/preprocessing.train_val_test_split`)
- [x] Синтетический smoke-тест пайплайна пройден
      (`notebooks/_synthetic_smoke_test.py`)
- [x] Capped multi-year Sentinel-2 patch sample создан и проверен
      (`data/processed/patches/sentinel2_multiyear_sample_2016_2024`,
      64 patches/year, 2016–2024; валидируется через
      `scripts/validate_patch_manifest.py`)
- [x] Multi-year training smoke-run выполнен
      (`src.train --patches-dir ... --model unet --epochs 1`; сохранены
      `models/unet_best_sentinel2_multiyear_sample_2016_2024` и
      `models/unet_final_sentinel2_multiyear_sample_2016_2024`; метрики
      smoke-run не являются production quality)
- [x] Temporal year-held-out split создан и проверен без дублирования массивов
      (`2016–2022 -> train`, `2023 -> validation`, `2024 -> test`;
      `scripts/build_year_holdout_manifest.py`,
      `data/processed/patches/sentinel2_year_holdout_2016_2024/manifest.json`)
- [x] Расширенный temporal dataset создан и провалидирован: 2 304 патча
      (2016–2024, 256/year), 14 каналов Sentinel-2 + terrain (elevation,
      slope, aspect), строгий split `2016–2022 -> train`, `2023 -> validation`,
      `2024 -> test`; mmap loader исключает полную загрузку набора в RAM
- [x] Capped temporal U-Net benchmark выполнен на strict year holdout:
      train `2016–2022`, validation `2023`, untouched test `2024`; на 14-channel
      Sentinel-2 + terrain sample test `Dice=0.7802`, `IoU=0.7382`,
      precision `0.9712`, recall `0.7547`
      (`results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json`).
      Это оценка в том же AOI с RGI-derived masks, не внешняя полевая валидация
      и не доказательство cross-region generalization.
- [ ] Full multi-year Sentinel-2 patch dataset создан и проверен
      (year-held-out strategy уже определена; требуется больше диска/времени)
- [x] Базовый EDA на реальных данных создан
      (`results/figures/eda_sentinel2_2020.png`,
      `results/tables/eda_sentinel2_2020.csv`)

## Месяц 4 — Базовые модели
- [x] NDSI пороговая классификация реализована (`03_baseline_models.ipynb`)
- [x] Random Forest реализован (`03_baseline_models.ipynb`)
- [x] Таблица базовых метрик заполнена реальными значениями (`results/tables/model_comparison.csv`)
- [x] Важность признаков RF проанализирована на реальных данных
      (`results/tables/random_forest_feature_importance.csv`,
      `results/figures/random_forest_feature_importance.png`; NDSI = 26.96%)

## Месяц 5–6 — U-Net
- [x] U-Net реализован, `model.summary()` без ошибок (проверено в
      `_unet_smoke_test.py`)
- [x] Модель обучена на реальных данных (F1=0.876, IoU=0.780; `models/unet_best.h5`)
- [x] Лучшие веса сохранены в `models/unet_best.h5`
- [x] Тест на тестовой выборке: F1 > 0.85 (цель достигнута: 0.8763)
- [x] Примеры предсказаний визуализированы (`results/figures/unet_test_samples.png`)
- [x] Сравнительная таблица методов заполнена реальными значениями
- [x] U-Net++ обучен (`models/unet_plus_plus_best.h5`) — F1=0.853

## Месяц 7–8 — Временной анализ
- [x] Код применения модели ко всем годам реализован
      (`05_temporal_analysis.ipynb`, `src/models.predict_full_image`)
- [x] Площади посчитаны на реальных данных, записаны в CSV
      (`results/tables/glacier_areas_all_years.csv`, `predictions/{year}/`)
- [x] Линейная регрессия и R² реализованы (`src/metrics.trend_analysis`)
- [x] Прогноз до 2050 реализован (`src/metrics.forecast_to_2050`)
- [x] Финальный график сохранён с реальными данными
      (`results/figures/glacier_trend_forecast.png`, `glacier_maps_by_year.png`)

## Месяц 9–12 — Публичная версия и валидация
- [x] Структура научной работы готова (`paper/draft_outline.md`)
- [x] Черновик заполнен реальными метриками из `results/` (см. `paper/results_template.md`)
- [x] Список литературы собран (`docs/literature_review.md`, 14 источников)
- [x] Decision-ready таблицы созданы с явными caveat/confidence полями
      (`results/tables/decision_ready_area_timeseries.csv`,
      `results/tables/year_quality_scores.csv`,
      `results/decision_readiness_summary.json`)
- [x] Decision-ready provenance gate добавлен и проходит
      (`scripts/validate_decision_readiness.py`,
      `tests/test_decision_readiness.py`)
- [x] Patch manifest gate добавлен для multi-year sample
      (`scripts/validate_patch_manifest.py`,
      `tests/test_patch_manifest.py`)
- [x] Training mask gate добавлен и проходит за 2016–2024
      (`scripts/build_year_masks.py`,
      `scripts/validate_training_masks.py`,
      `tests/test_training_masks.py`)
- [x] Dashboard/API/MCP читают decision-readiness пакет
      (`/api/data/decision-readiness`, `glacierkz://decision-readiness`)
- [x] Stakeholder outreach pack и трекер подготовлены
      (`docs/STAKEHOLDER_OUTREACH_PACK.md`,
      `docs/stakeholder_outreach_tracker.csv`)
- [x] Project evidence package можно пересобрать одной командой
      (`scripts/build_project_evidence_package.py`)
- [ ] Работа проверена внешним специалистом или научным консультантом
- [x] Подготовлен публичный demo walkthrough (`docs/DEMO_WALKTHROUGH.md`)
- [x] Подготовлен локальный release package и gate для GitHub
      (`docs/RELEASE_PACKAGE.md`, `scripts/verify_local_release_package.py`)
- [ ] Проведены 3+ воспроизводимых demo-прогона

---

## Дополнительные идеи из исследовательской базы (Блок "После поиска")

- [x] Идея A: WGMS-валидация — 25 лет FoG (1958–2025), RMSE proxy 0.335 km²
      (`results/wgms_validation_report.json`, `scripts/run_wgms_validation.py`)
- [ ] Идея B: SAM как zero-shot baseline (опционально, `segment-geospatial`)
- [x] Идея C: Угроза водоснабжению Алматы — код готов
      (`src/metrics.ice_volume_loss_to_water_supply`)
- [x] Идея D: Uncertainty Quantification (MC-Dropout) — код готов
      (`src/models.mc_dropout_predict`)
- [ ] Идея E: Письма партнёрам (см. `docs/contacts_and_partnerships.md`)
