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
- [x] Маски ледников созданы (2020 + многолетние предсказания в `predictions/`)
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
- [ ] Multi-year Sentinel-2 patch dataset создан и проверен
- [ ] Базовый EDA на реальных данных (гистограммы, примеры снимков + масок)

## Месяц 4 — Базовые модели
- [x] NDSI пороговая классификация реализована (`03_baseline_models.ipynb`)
- [x] Random Forest реализован (`03_baseline_models.ipynb`)
- [x] Таблица базовых метрик заполнена реальными значениями (`results/tables/model_comparison.csv`)
- [ ] Важность признаков RF проанализирована на реальных данных

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

## Месяц 9–12 — Подготовка к конкурсам
- [x] Структура научной работы готова (`paper/draft_outline.md`)
- [x] Черновик заполнен реальными метриками из `results/` (см. `paper/results_template.md`)
- [x] Список литературы собран (`docs/literature_review.md`, 14 источников)
- [x] Decision-ready таблицы созданы с явными caveat/confidence полями
      (`results/tables/decision_ready_area_timeseries.csv`,
      `results/tables/year_quality_scores.csv`,
      `results/decision_readiness_summary.json`)
- [x] Dashboard/API/MCP читают decision-readiness пакет
      (`/api/data/decision-readiness`, `glacierkz://decision-readiness`)
- [x] Stakeholder outreach pack и трекер подготовлены
      (`docs/STAKEHOLDER_OUTREACH_PACK.md`,
      `docs/stakeholder_outreach_tracker.csv`)
- [x] Project evidence package можно пересобрать одной командой
      (`scripts/build_project_evidence_package.py`)
- [ ] Работа проверена учителем / научным руководителем
- [ ] Зарегистрирован на Дарын
- [x] Подготовлен постер — черновик `competition/ISEF_POSTER.md`
- [x] Подготовлена презентация (7 минут) — `competition/ISEF_PRESENTATION.md`
- [ ] Проведено 3+ репетиции защиты

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
