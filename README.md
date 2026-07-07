# GlacierNET-KZ

[English version](README.en.md) · [Documentation](docs/README.md) · [Reproducibility](docs/REPRODUCIBILITY.md) · [Citation (CITATION.cff)](CITATION.cff) · [Contributing](CONTRIBUTING.md)

[![CI](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/GlacierNET-KZ/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![HuggingFace Spaces](https://img.shields.io/badge/🤗-Live_Demo-yellow)](https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2)

ML-мониторинг отступания ледников Казахстана (Заилийский Алатау / Джунгарский Алатау)
с помощью U-Net и спутниковых снимков Sentinel-2 / Landsat.

Проект для научных конкурсов **Дарын → ISEF → GENIUS Olympiad**.
Научная база и план — см. `docs/`.

---

## Описание проекта

**GlacierNET-KZ** — открытая исследовательская и прикладная платформа для мониторинга ледников Казахстана по спутниковым данным. Проект объединяет Sentinel-2, Landsat, RGI/WGMS, классические спектральные индексы и ML-модели, чтобы строить карты ледников, измерять изменение площади, оценивать качество данных по годам и формировать отчёты для исследователей, преподавателей, госорганов и организаций, работающих с климатическими и водными рисками.

Основная идея проста: вместо ручной обработки снимков в GIS пользователь получает воспроизводимый pipeline, web-dashboard, API и MCP-интерфейс, которые показывают не только результат модели, но и ограничения данных: сенсор, caveat, confidence score, p-value, 95% CI и годы, исключённые из строгого тренда.

Ключевые сценарии:
- научный анализ изменения ледников Заилийского Алатау за 2000–2024;
- быстрые decision reports для не-технических пользователей;
- сравнение NDSI, Random Forest и U-Net на реальных данных;
- подготовка пилотов по климатическому мониторингу и водной безопасности;
- образовательная демонстрация полного ML/geospatial pipeline.

---

## Статус проекта

Код пайплайна полностью реализован и протестирован на **реальных данных** (2000–2024).
Результаты доступны в `results/` и `paper/results_template.md`.

- [x] Структура проекта создана
- [x] `src/` — модули предобработки, U-Net, метрик, визуализации
- [x] 6 Jupyter-ноутбуков (01–06) с кодом по плану
- [x] Сквозной тест пайплайна на синтетических данных пройден
- [x] Реальные снимки Sentinel-2 (2015–2024) — compact 7-band или legacy 11-band GeoTIFF; 2015 задокументирован как late-year TOA fallback
- [x] Реальные снимки Landsat (2000, 2003, 2005, 2008, 2010, 2013) скачаны
- [x] RGI 7.0 контуры ледников загружены и растеризованы
- [x] Data quality, inventory и STAC-артефакты обновлены (`results/data_quality_report.json`, `results/tables/data_inventory.csv`, `results/stac/catalog.json`)
- [x] Маски построены, патчи нарезаны
- [x] Базовые модели (NDSI, Random Forest) обучены на реальных данных
- [x] U-Net обучен на реальных данных (F1=0.876, IoU=0.780)
- [x] Временной анализ и прогноз до 2050 построены
- [x] WGMS-валидация (Туюксу) — данные из FoG 2026 (`data/wgms/tuyuksu_areas.json`, 25 лет)
- [x] Научная работа заполнена реальными данными

### Ключевые результаты

| Метрика | Значение |
|---------|----------|
| U-Net F1 | 0.876 |
| Random Forest F1 | 0.853 |
| NDSI F1 | 0.851 |
| Потеря ледников 2000–2020 | −129.5 км² (−22.4%) |
| Скорость потерь | −12.7 км²/год |
| Прогноз 2050 | ~350 км² (−38% от 2000) |
| Эквивалент водоснабжения Алматы | ~10 лет |

---

## Международные стандарты

| Стандарт | Реализация |
|----------|------------|
| Открытая наука | MIT, полный исходный код, HuggingFace demo |
| FAIR | [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) |
| Геоданные | STAC 1.0, GeoTIFF, [DATA_CITATION.md](docs/DATA_CITATION.md) |
| i18n | Dashboard EN / RU / KK |
| Конкурсы | [ISEF](competition/ISEF_POSTER.md), [GENIUS](competition/GENIUS_OLYMPIAD.md) |

---

## Единый localhost

```bash
./scripts/start.sh
# → http://localhost:8080/hub
```

| Сервис | URL |
|--------|-----|
| Хаб | http://localhost:8080/hub |
| Dashboard | http://localhost:8080/dashboard |
| Gradio демо | http://localhost:8080/demo |
| API docs | http://localhost:8080/docs |
| MCP | http://localhost:8080/mcp/tools |

🏔️ [HuggingFace Spaces](https://huggingface.co/spaces/dulatnurlanuly/codedepo-v2) — облачная демо-версия.

---

## Структура проекта

```
GlacierNET-KZ/
├── data/
│   ├── raw/
│   │   ├── sentinel2/      # Sentinel-2 композиты (скачать через 01_data_download.ipynb)
│   │   └── landsat/        # Landsat композиты
│   ├── processed/
│   │   ├── patches/         # X_train.npy, y_train.npy, ...
│   │   └── masks/           # Маски ледников по годам
│   └── rgi/                 # Контуры RGI 7.0 / GLIMS
│
├── notebooks/
│   ├── 01_data_download.ipynb     # GEE: Sentinel-2, Landsat, RGI (ЛОКАЛЬНО, требует GEE auth)
│   ├── 02_preprocessing.ipynb     # Маски, патчи, train/val/test
│   ├── 03_baseline_models.ipynb   # NDSI, Random Forest
│   ├── 04_unet_training.ipynb     # Обучение U-Net
│   ├── 05_temporal_analysis.ipynb # Временной анализ, прогноз 2050, WGMS, водоснабжение
│   ├── 06_visualization.ipynb     # Финальные карты и графики
│   ├── _generate_notebooks.py     # Генератор .ipynb из исходного кода (для git-ревью)
│   ├── _synthetic_smoke_test.py   # Сквозной тест пайплайна без TF
│   └── _unet_smoke_test.py        # Сквозной тест U-Net
│
├── src/
│   ├── config.py          # Все константы: область, годы, каналы, гиперпараметры
│   ├── data_loader.py      # GEE загрузка + чтение GeoTIFF (rasterio)
│   ├── preprocessing.py    # Растеризация RGI, патчи, аугментация, split
│   ├── models.py            # U-Net, Dice/BCE loss, генератор данных, MC-Dropout
│   ├── metrics.py           # F1/IoU, тренд, прогноз 2050, WGMS RMSE, водоснабжение
│   └── visualization.py     # RGB/маски, кривые обучения, карты, прогноз
│
├── models/                  # Сохранённые модели (random_forest.pkl, unet_best.h5, attention_unet_best.h5)
├── glacierkz-api/           # FastAPI backend (REST + WebSocket + MCP bridge)
├── glacierkz-web/           # Next.js 16 dashboard (en/ru/kk i18n)
├── glacierkz-mcp/           # MCP server for LLM tool access
├── experimental/          # Phase 9 multi-lang prototypes (C, C++, Go, Java, .NET)
├── tests/                   # Pytest suite (334+ tests)
├── .github/workflows/       # CI: Ruff, pytest, Pyright, Vitest, ESLint, Playwright, Docker
├── results/
│   ├── figures/             # Графики (PNG)
│   └── tables/              # CSV таблицы результатов
├── spaces/                  # HuggingFace Spaces Gradio app
├── paper/                    # Научная работа
├── docs/
│   ├── README.md              # Индекс документации
│   ├── REPRODUCIBILITY.md     # FAIR / воспроизводимость (международный стандарт)
│   ├── DATA_CITATION.md       # BibTeX для Sentinel-2, Landsat, RGI, WGMS
│   └── literature_review.md   # Обзор литературы (из research_database)
└── requirements.txt
```

---

## Быстрый старт (локально, не в облачной песочнице)

GEE-аутентификация, скачивание Sentinel-2/Landsat/RGI и обучение U-Net
**требуют локальной машины** с доступом в интернет — облачная среда,
в которой был сгенерирован этот код, не имеет доступа к Earth Engine,
NSIDC/GLIMS, WGMS или Google Drive.

### 1. Установка окружения

```bash
conda create -n glaciers python=3.10
conda activate glaciers
conda install -c conda-forge gdal rasterio geopandas shapely fiona
pip install -r requirements.txt
```

> Примечание: TensorFlow 2.13 требует `numpy<1.24.4`. Если возникает
> конфликт версий numpy/scipy/scikit-learn, поставьте `numpy==1.26.4`
> ПОСЛЕ tensorflow (как сделано в этом проекте) — TF 2.13 фактически
> работает и с numpy 1.26. Архитектура U-Net в `src/models.py`
> совместима с любой версией TensorFlow >= 2.10.

### 2. Аутентификация Earth Engine

```bash
earthengine authenticate
```

### 3. Скачивание данных

Откройте `notebooks/01_data_download.ipynb`, выполните все ячейки.
Задачи экспорта появятся на https://code.earthengine.google.com/tasks.
После завершения скачайте файлы из Google Drive (папка `GlacierKZ`) в
`data/raw/sentinel2/` и `data/raw/landsat/`.

Контуры RGI 7.0 (регион 13, Central Asia) также можно скачать вручную с
https://www.glims.org/RGI/rgi70_dl.html и положить shapefile в `data/rgi/`.

### 4. Запуск пайплайна

```
02_preprocessing.ipynb     -> data/processed/patches/*.npy
03_baseline_models.ipynb   -> models/random_forest.pkl, results/tables/model_comparison.csv
04_unet_training.ipynb     -> models/unet_best.h5
05_temporal_analysis.ipynb -> results/tables/glacier_areas_*.csv, прогноз до 2050
06_visualization.ipynb     -> results/figures/*.png
```

### 5. Проверка кода без данных (синтетический тест)

```bash
python notebooks/_synthetic_smoke_test.py
python notebooks/_unet_smoke_test.py
python scripts/validate_data_quality.py
python scripts/build_data_inventory.py
python scripts/export_stac_catalog.py   # STAC 1.0 каталог для QGIS
```

---

## Целевые ледники

См. `src/config.py` → `GLACIERS`. Приоритет №1 — **Горный Туюксу**
(WGMS reference glacier, данные с 1957 г.).

## Научная новизна

См. `docs/literature_review.md`. Ключевой тезис (Springer 2025, обзор DL+Казахстан):
ML-методов для ледников Тянь-Шаня и Джунгарского Алатау в литературе
практически нет — это ниша проекта.

## Лицензия

См. `LICENSE`.
