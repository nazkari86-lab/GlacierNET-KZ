# GlacierNET-KZ — Полная справочная документация проекта

> Дата создания: Июнь 2026
> Статус: Пайплайн полностью реализован, обучен на реальных данных (2000–2020), 322 теста проходят
> Лицензия: MIT (c) 2026 nazkari86-lab
> Назначение: open-source geospatial AI platform for glacier monitoring

---

## Содержание

1. [Обзор проекта](#1-обзор-проекта)
2. [Структура директорий](#2-структура-директорий)
3. [Архитектура системы](#3-архитектура-системы)
4. [Описание каждого файла](#4-описание-каждого-файла)
5. [Пайплайн обработки данных](#5-пайплайн-обработки-данных)
6. [Модели машинного обучения](#6-модели-машинного-обучения)
7. [API эндпоинты](#7-api-эндпоинты)
8. [Фронтенд](#8-фронтенд)
9. [Инфраструктура и DevOps](#9-инфраструктура-и-devops)
10. [Тестирование](#10-тестирование)
11. [Roadmap](#11-roadmap)

---

## 1. Обзор проекта

**GlacierNET-KZ** — система мониторинга отступания ледников Казахстана (Заилийский Алатау / Джунгарский Алатау) с использованием глубокого обучения (U-Net) и спутниковых снимков Sentinel-2/Landsat.

### Ключевые результаты

| Метрика | Значение |
|---------|----------|
| Лучшая модель | Attention U-Net |
| F1-score | 0.876 |
| IoU | 0.779 |
| Потери ледников (2000–2020) | -22.4% |
| Прогноз к 2050 | Дальнейшее отступание |
| Количество тестов | 322 (все проходят) |
| Код | ruff lint чистый |

### Технологический стек

| Компонент | Технологии |
|-----------|-----------|
| Backend | FastAPI 0.109.0, Python 3.10, TensorFlow 2.21, NumPy 1.26, Redis |
| Frontend | Next.js 16.2.9, React 19, TypeScript, Tailwind CSS, Leaflet, Recharts |
| ML | U-Net, Attention U-Net, U-Net++, Random Forest, NDSI, ансамбль (5 моделей) |
| Спектральные каналы | 7 спутниковых полос Sentinel-2 + 4 индекса (NDSI, NDWI, BSI, EVI) = 11 каналов |
| Инференス | Скользящее окно 256×256, 50% перекрытие, TTA (3 отражения), MC-Dropout неопределённость |
| Обучение | 70/15/15 split, batch=8, 100 эпох, Adam 1e-4, ReduceLROnPlateau + EarlyStopping + TensorBoard |
| LLM | liteLLM (мути-провайдер) + Ollama (локальный) |
| CI/CD | GitHub Actions (lint + test + typecheck + security + docker-build) |
| Контейнеры | Docker Compose (Redis + API + Web) |

---

## 2. Структура директорий

```
GlacierNET-KZ/
├── glacierkz-api/           # FastAPI backend (порт 8000)
│   ├── app/
│   │   ├── main.py          # Точка входа FastAPI
│   │   ├── config.py        # Конфигурация (плоские переменные)
│   │   ├── utils.py         # Утилиты (resolve_core_dir, path_to_url)
│   │   ├── worker.py        # Celery worker (не используется)
│   │   ├── mcp_tools.py     # MCP инструменты для ИИ-агентов
│   │   ├── routers/         # 14 файлов маршрутов API
│   │   ├── routes/          # 9 файлов дополнительных маршрутов
│   │   ├── services/        # 8 файлов бизнес-логики
│   │   ├── storage/         # 3 файла хранилища данных
│   │   ├── schemas/         # Pydantic модели запросов/ответов
│   │   ├── auth/            # JWT, API ключи, RBAC
│   │   ├── middleware/       # Кэш,.rate limit, логирование, заголовки
│   │   ├── monitoring/      # Health check, метрики Prometheus
│   │   ├── ws/              # WebSocket менеджер
│   │   ├── tasks/           # Менеджер фоновых задач
│   │   └── static/          # Встроенный HTML UI (864 строки)
│   ├── Dockerfile
│   ├── seed_db.py           # Заполнение БД результатами сегментации
│   └── requirements-api.txt
│
├── glacierkz-web/           # Next.js frontend (порт 3000)
│   ├── src/
│   │   ├── app/             # 20 страниц (App Router)
│   │   ├── components/      # 35 React компонентов
│   │   ├── lib/             # 9 утилит (API клиент, i18n, auth, ...)
│   │   └── __tests__/       # 14 тестов фронтенда
│   ├── Dockerfile
│   └── package.json
│
├── src/                     # Core ML Python пакет (39 модулей)
│   ├── config.py            # Центральная конфигурация ML
│   ├── models.py            # U-Net, Attention U-Net, U-Net++, генераторы
│   ├── data_loader.py       # Загрузка с GEE и rasterio
│   ├── preprocessing.py     # Растеризация RGI, патчи, аугментация
│   ├── metrics.py           # F1, IoU, тренд, прогноз до 2050
│   ├── visualization.py     # Визуализация результатов
│   ├── train.py             # CLI обучение
│   ├── losses.py            # 10 функций потерь
│   ├── segmentation_models.py # FCN, DeepLabV3, PSPNet, LinkNet, ...
│   ├── augmentation.py      # Геометрическая, фотометрическая, спектральная
│   ├── evaluation.py        # Пиксельные и региональные метрики
│   ├── ensemble.py          # Ансамбли (взвешенное усреднение, голосование)
│   ├── callbacks.py         # Keras callbacks
│   ├── schedulers.py        # LR планировщики
│   ├── uncertainty.py       # MC-Dropout, калибровка
│   ├── postprocessing.py    # Морфология, CRF, фильтрация
│   ├── spectral.py          # Спектральные индексы (NDSI, NDVI, NDWI, ...)
│   ├── anomaly.py           # Детекция аномалий
│   ├── clustering.py        # K-means, иерархическая кластеризация
│   ├── feature_engineering.py # Текстура GLCM, спектральные признаки
│   ├── interpretability.py  # Grad-CAM, attention rollout, Shapley
│   ├── datasets.py          # Управление датасетами
│   ├── vision_transformer.py # ViT для спутниковых снимков
│   ├── diffusion_model.py   # DDPM для супер-решения
│   ├── domain_adaptation.py # Перенос между сенсорами
│   ├── multi_task_learning.py # Многозадачная модель
│   ├── experiment_tracking.py # Логирование экспериментов
│   ├── hyperparameter_tuning.py # Grid/Random/Bayesian search
│   ├── benchmarking.py      # Замеры производительности
│   ├── model_compression.py # Квантизация, прунинг
│   ├── neural_architecture_search.py # NAS
│   ├── self_supervised.py   # SimCLR, BYOL, MoCo
│   ├── active_learning.py   # Стратегии активного обучения
│   ├── graph_neural_network.py # GNN для связности ледников
│   ├── federated_learning.py # Федеративное обучение
│   ├── distributed_training.py # Распределённое обучение
│   ├── time_series.py       # Временные ряды, тренды
│   └── reporting.py         # Генерация отчётов
│
├── spaces/                  # HuggingFace Spaces (Gradio)
│   ├── app.py               # Gradio приложение
│   ├── README.md
│   ├── requirements.txt
│   └── examples/
│
├── tests/                   # 27 тестовых файлов Python
├── notebooks/               # 12 файлов (6 основных + утилиты)
├── docs/                    # 8 документов
├── paper/                   # Научная статья
├── scripts/                 # Утилиты
├── plans/                   # Планирование
├── models/                  # Обученные веса
├── results/                 # Результаты
├── predictions/             # Предсказания по годам
├── data/                    # Данные
│   ├── raw/sentinel2/       # Sentinel-2 GeoTIFF
│   ├── raw/landsat/         # Landsat GeoTIFF
│   ├── processed/masks/     # Маски ледников
│   ├── processed/patches/   # Патчи для обучения (.npy)
│   └── rgi/                 # Файлы RGI 7.0
│
├── docker-compose.yml       # 3 сервиса: Redis, API, Web
├── requirements.txt         # Python зависимости
├── pyproject.toml           # Конфигурация проекта
├── predict.py               # CLI для предсказаний
├── download_drive.py        # Скачивание с Google Drive
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 3. Архитектура системы

### 3.1. Три уровня (Three-Tier)

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                    │
│  Порт 3000 │ React 19 │ Tailwind │ Leaflet │ Recharts   │
├─────────────────────────────────────────────────────────┤
│                    API Gateway (FastAPI)                 │
│  Порт 8000 │ Middleware │ Auth │ Rate Limit │ Cache      │
├─────────────────────────────────────────────────────────┤
│                    ML Core (src/)                        │
│  TensorFlow │ U-Net │ Preprocessing │ Metrics            │
├─────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  SQLite (WAL) │ Redis │ Файловая система                │
└─────────────────────────────────────────────────────────┘
```

### 3.2. Стек.middleware FastAPI

Запрос проходит через 4 middleware (порядок важен):

1. **SecurityHeadersMiddleware** — CSP, HSTS, X-Frame-Options, X-XSS-Protection
2. **RequestLoggingMiddleware** — Structured logging с request ID, timing
3. **CacheMiddleware** — In-memory GET кэш с ETag, TTL
4. **RateLimitMiddleware** — Token bucket (per-minute/per-hour), Redis или in-memory

### 3.3. Аутентификация

- **API Key** — SHA-256 хэш, scope (read/write/admin), заголовок или query param
- **JWT** — HS256/RS256, access/refresh токены, claims
- **RBAC** — 3 роли: Viewer, Analyst, Admin с маппингом scope

### 3.4. Пайплайн ML

```
GeoTIFF/Landsat → Загрузка (rasterio) → Спектральные индексы (11 каналов)
→ Патчи 256×256 (50% overlap) → U-Net/Attention U-Net → Постпроцессинг
→ Маска ледника → Расчёт площади → Экспорт (PNG/NPY/GeoJSON)
```

### 3.5. LLM Gateway

```
Запрос → litellm → Выбор провайдера (OpenAI/Anthropic/Groq/Gemini/Ollama)
→ Системный промпт (гляциолог) → Анализ → Ответ
```

---

## 4. Описание каждого файла

### 4.1. Топ-уровень проекта

| Файл | Назначение |
|------|-----------|
| `README.md` | Обзор проекта на русском. Описание структуры, быстрый старт, ключевые результаты |
| `AGENTS.md` | Контекст для ИИ-агентов: стек, соглашения, CI/CD, критические находки |
| `CONTRIBUTING.md` | Руководство по вкладу: настройка, стиль кода (ruxx), структура проекта |
| `LICENSE` | MIT Лицензия |
| `pyproject.toml` | Конфигурация: Python >=3.10, ruff (line-length=120), pytest (testpaths=tests) |
| `requirements.txt` | Python зависимости: tensorflow>=2.12, numpy>=1.24, scikit-learn, rasterio, geopandas, ... |
| `docker-compose.yml` | 3 сервиса: redis:7-alpine (6379), api (FastAPI, 8000), web (Next.js, 3000). Health checks |
| `.gitignore` | Игнорирует __pycache__, .env, node_modules, .db, results/, predictions/ |
| `predict.py` | CLI инструмент: загрузка спутниковых TIF по годам → NDSI/RF/U-Net/ансамбль → сохранение масок |
| `download_drive.py` | Скачивание GeoTIFF из Google Drive через OAuth2. Читает credentials из `GOOGLE_CLIENT_SECRET` env |
| `drive_file_list.json` | JSON список файлов в папке Google Drive |
| `download.log` | Лог файл операций скачивания |

### 4.2. glacierkz-api/ — FastAPI Backend

#### app/ — Главный пакет

| Файл | Назначение |
|------|-----------|
| `app/__init__.py` | Инициализация пакета |
| `app/main.py` | Точка входа FastAPI. CORS, middleware стек (4 шт.), подключение static, роутеров, WebSocket, lifespan |
| `app/config.py` | Центральная конфигурация: пути (DATA_DIR, UPLOAD_DIR, RESULTS_DIR), REDIS_URL, CORS_ORIGINS, MAX_FILE_SIZE, LLM настройки. **Плоские переменные модуля**, без объекта `settings` |
| `app/utils.py` | `resolve_core_dir()` — находит пакет src/ через CORE_DIR env. `path_to_url()` — конвертирует пути файлов в static URL |
| `app/worker.py` | Celery worker (не используется — вся сегментация синхронная) |
| `app/mcp_tools.py` | MCP инструменты для ИИ-агентов: спектральный анализ, сегментация, временные ряды. 740 строк |

#### app/routers/ — 14 файлов маршрутов API

| Файл | Маршруты | Назначение |
|------|----------|-----------|
| `segmentation.py` | `POST /api/predict`, `GET /api/predict/{task_id}` | Загрузка изображения + выбор модели → маска сегментации |
| `models.py` | `GET /api/models`, `GET /api/models/available` | Список 6 моделей (unet, attention_unet, unet_plus_plus, ndsi, rf, ensemble) |
| `compare.py` | `POST /api/compare` | Загрузка изображения, запуск нескольких моделей, результаты рядом |
| `area.py` | `POST /api/area` | Расчёт площади ледника из маски (км²) |
| `history.py` | `GET /api/history`, `DELETE /api/history/{task_id}` | Список прошлых сегментаций, удаление |
| `export.py` | `GET /api/export/{task_id}`, `GET /api/export/{task_id}/stats` | Экспорт маски (png/npy/csv/json/geojson) |
| `trend.py` | `POST /api/trend` | Многолетний тренд с прогнозом до 2050 |
| `uncertainty.py` | `POST /api/uncertainty` | MC-Dropout оценка неопределённости (синхронная → `asyncio.to_thread`) |
| `analysis.py` | `GET /api/analysis/models`, `POST /api/analysis/analyze` | LLM анализ ледников (describe/trend/compare) |
| `admin.py` | `GET /api/admin/status`, `GET/PUT /api/admin/config`, `GET/POST /api/admin/users`, `DELETE`, `GET /api/admin/audit`, `GET /api/admin/logs` | Администрирование |
| `notifications.py` | CRUD уведомлений | Конфигурация, отправка, список, прочтение |
| `reports.py` | `GET /training/latest`, `GET /inference/latest`, `GET /summary/daily`, `GET /{report_id}`, `DELETE /{report_id}`, `POST /export/{report_id}` | Генерация/список/экспорт отчётов |

#### app/routes/ — 9 файлов дополнительных маршрутов

| Файл | Назначение |
|------|-----------|
| `admin.py` | Дублирование/расширение admin из routers/ |
| `datasets.py` | Управление датасетами: список, создание, загрузка, валидация, инспекция |
| `export.py` | Экспорт (маски, предсказания, модели, geojson) |
| `monitoring.py` | Prometheus-совместимые метрики, системная информация, health/status |
| `notifications.py` | Уведомления (дублирование из routers/) |
| `reports.py` | Отчёты (дублирование из routers/) |
| `tasks.py` | CRUD фоновых задач: создание, список, получение, отмена с state machine |
| `training.py` | Управление обучением: start/stop/resume, список моделей, конфигурация, история |
| `ws.py` | WebSocket маршруты: ConnectionManager с topic-based pub/sub |

#### app/services/ — 8 файлов бизнес-логики

| Файл | Назначение |
|------|-----------|
| `segmentation_service.py` | **Ядро ML**: загрузка Keras моделей (U-Net, Attention U-Net, U-Net++), RF модель, инференс со скользящим окном, TTA, генерация масок/оверлеев. Потокобезопасный кэш моделей с lock |
| `llm_service.py` | LLM шлюз через litellm: мульти-провайдер (OpenAI, Anthropic, Groq, Google, Ollama, OpenRouter) с fallback, системные промпты для гляциолога |
| `area_service.py` | Расчёт площади ледника из маски (TIF через rasterio или PNG через PIL) |
| `trend_service.py` | Многолетний тренд и прогноз до 2050 через core функции metrics |
| `export_service.py` | Экспорт: маски в numpy/png, предсказания в JSON/CSV/GeoJSON, экспорт TF моделей. 333 строки |
| `notification_service.py` | Система уведомлений: console/email/webhook каналы, шаблоны, история. 318 строк |
| `report_service.py` | Генерация отчётов: training/inference/summary, шаблоны, агрегация метрик. 381 строка |
| `admin_service.py` | Администрирование: системные метрики (CPU/memory/disk), статус сервисов, лог операций, алерты. 382 строки |

#### app/storage/ — 3 файла хранилища

| Файл | Назначение |
|------|-----------|
| `results.py` | SQLite хранилище результатов сегментации: save_result, get_result, get_history, delete_result. WAL mode, авто-инициализация схемы |
| `uploads.py` | Обработка загрузки файлов: валидация расширений (.tif/.tiff/.png/.jpg/.jpeg), проверка макс. размера, сохранение с UUID |
| `analysis_history.py` | SQLite хранилище истории LLM анализов |

#### app/schemas/ — Pydantic модели

| Файл | Модели |
|------|--------|
| `requests.py` | `TrendRequest`, `LLMAnalyzeRequest` |
| `responses.py` | `ModelInfo`, `SegmentationResult`, `CompareResult`, `AreaResponse`, `UncertaintyResult`, `TrendResult`, `HistoryItem`, `ExportResponse`, `LLMAnalyzeResponse`, `LLMProviderInfo` |

#### app/auth/ — Аутентификация

| Файл | Назначение |
|------|-----------|
| `api_key.py` | API ключ: генерация, хэширование (SHA-256), валидация, проверка scope, заголовок/query param |
| `jwt_auth.py` | JWT: HS256/RS256, access/refresh токены, claims, верификация |
| `rbac.py` | RBAC: 3 роли (Viewer/Analyst/Admin), маппинг scope, dependency injection для FastAPI |

#### app/middleware/ — HTTP Middleware

| Файл | Назначение |
|------|-----------|
| `cache.py` | In-memory HTTP кэш для GET с ETag, TTL, макс. размер, exempt пути |
| `rate_limit.py` | Token bucket rate limiting (per-minute/per-hour), Redis или in-memory fallback |
| `request_logging.py` | Структурированное логирование с timing, request ID, маскировка чувствительных заголовков |
| `security_headers.py` | Безопасные заголовки: CSP, HSTS, X-Frame-Options, X-XSS-Protection, Referrer-Policy, COEP/COOP/CORP |

#### app/monitoring/ — Observability

| Файл | Назначение |
|------|-----------|
| `health.py` | Health check: liveness/readiness probes, глубокие проверки, статус зависимостей |
| `metrics.py` | Prometheus-совместимые метрики: counters, gauges, histograms, render в text |
| `system.py` | Системная информация: платформа, Python, GPU, диск, процессы, лимиты памяти |

#### app/ws/ — WebSocket

| Файл | Назначение |
|------|-----------|
| `handlers.py` | WebSocket обработчик: connect, ping/pong, join/leave room, broadcast, stats |
| `manager.py` | ConnectionManager: rooms, pub/sub, heartbeat loop, broadcast loop, отслеживание клиентов |

#### app/tasks/ — Фоновые задачи

| Файл | Назначение |
|------|-----------|
| `manager.py` | Менеджер задач: приоритетная очередь, жизненный цикл (pending/running/completed/failed/cancelled), прогресс, таймауты, повторы |

#### app/static/ — Встроенный HTML UI

| Файл | Назначение |
|------|-----------|
| `index.html` | 864-строчный standalone HTML/JS/CSS UI. Тёмная тема, sidebar навигация, поддержка сегментации, сравнения, трендов, истории, экспорта |

### 4.3. glacierkz-web/ — Next.js Frontend

#### src/app/ — 20 страниц (App Router)

| Страница | Файл | Назначение |
|----------|------|-----------|
| Корень | `page.tsx` | Домашняя: GlacierHero, навигационная сетка (10 пунктов), LanguageSwitcher |
| Dashboard | `dashboard/page.tsx` | Стат. карточки, line chart (сегменты), donut chart (модели), таблица задач |
| Predict | `predict/page.tsx` | Загрузка, выбор модели, TTA/CRF, NDSI threshold → карта с оверлеем |
| Compare | `compare/page.tsx` | Загрузка, 2+ модели, SplitView результатов |
| Trend | `trend/page.tsx` | Год+файл, анализ тренда, TrendChart с прогнозом |
| History | `history/page.tsx` | Список прошлых сегментаций, просмотр на карте |
| Analysis | `analysis/page.tsx` | Выбор LLM провайдера, промпт, режим (describe/trend/compare) |
| Pipeline | `pipeline/page.tsx` | Запуски пайплайна, этапы (ingest/preprocess/segment/evaluate/deploy) |
| Training | `training/page.tsx` | Гиперпараметры, start/pause/stop, loss chart, логи, прогресс |
| Datasets | `datasets/page.tsx` | Список датасетов, загрузка, статус (validated/pending/processing) |
| Reports | `reports/page.tsx` | Таблица моделей, тренды, donut, экспорт в CSV/JSON/PDF |
| Settings | `settings/page.tsx` | Вкладки: General, Language (en/ru/kk), Notifications, Security, Data |
| Admin | `admin/page.tsx` | Обзор: системные статы, алерты, real-time chart |
| Admin/Users | `admin/users/page.tsx` | Управление пользователями |
| Admin/Audit | `admin/audit/page.tsx` | Аудит лог |
| Admin/System | `admin/system/page.tsx` | Мониторинг системы |

#### src/components/ — 35 React компонентов

| Компонент | Назначение |
|-----------|-----------|
| `ActivityFeed` | Лента активности в реальном времени |
| `AdminDataTable` | Таблица данных для админа |
| `Badges` | Статус/badge элементы |
| `Breadcrumb` | Навигационные хлебные крошки |
| `Charts` | LineChart, DonutChart (обёртки Recharts) |
| `ConfirmationDialog` | Модальное подтверждение |
| `DatasetUploader` | Загрузка датасетов |
| `DataTable` | Универсальная сортируемая таблица с пагинацией |
| `ErrorBoundary` | React error boundary с fallback UI |
| `ExperimentLog` | Отображение лога экспериментов |
| `FileExplorer` | Проводник файлов |
| `Forms` | Компоненты форм |
| `GlacierHero` | Hero баннер для домашней страницы |
| `HistoryTable` | Таблица результатов истории |
| `LanguageSwitcher` | Переключатель языков (en/ru/kk) |
| `LoadingOverlay` | Оверлей загрузки |
| `MapView` | Leaflet карта для отображения geo результатов |
| `MapViewExtended` | Расширенная карта |
| `MetricChart` | Визуализация метрик |
| `MetricGauge` | Метрический gauge/bar |
| `Modal` | Переиспользуемый модальный диалог |
| `ModelSelector` | Выпадающий список/карточки моделей |
| `PipelineStage` | Визуализация этапа пайплайна |
| `RealTimeChart` | Real-time обновляемый график |
| `SearchBar` | Поле поиска |
| `Skeletons` | Skeleton загрузки |
| `SplitView` | Сравнение бок о бок |
| `StatCard` | Карточка статистики с индикатором тренда |
| `TabsAccordion` | Вкладки и аккордеон |
| `Toast` | Система toast уведомлений |
| `TrainingWizard` | Пошаговый мастер конфигурации обучения |
| `TrendChart` | График тренда с прогнозом |
| `UploadZone` | Drag-and-drop зона загрузки |
| `UserAvatar` | Аватар пользователя |
| `WebGLMap` | WebGL ускоренная карта |

#### src/lib/ — 9 утилит

| Файл | Назначение |
|------|-----------|
| `api.ts` | TypeScript интерфейсы + fetch функции для всех эндпоинтов |
| `auth.ts` | Управление токенами/пользователями в localStorage, login/logout/refresh |
| `constants.ts` | API эндпоинты, роли, статусы, этапы пайплайна, цвета |
| `export.ts` | Экспорт: CSV, JSON, PDF с auto-table |
| `i18n.ts` | Интернационализация: 900 строк переводов для en/ru/kk, 100+ ключей |
| `I18nProvider.tsx` | React context provider для i18n |
| `utils.ts` | cn (tailwind-merge), apiUrl, formatBytes/Number/Date, debounce, throttle, downloadFile, generateId |
| `validators.ts` | Валидация форм: required, min/max, pattern, custom |
| `websocket.ts` | WebSocket клиент: reconnect, heartbeat, event listeners, статус |

### 4.4. src/ — Core ML Python пакет (39 модулей)

#### Основные модули

| Файл | Назначение | Строки |
|------|-----------|--------|
| `__init__.py` | Lazy imports для 30+ подмодулей (избегает дорогих TF/cv2 импортов) | — |
| `config.py` | Центральная конфигурация: пути, bbox, координаты ледников (Туюксу, Богданович, Мутный), годы, спектральные полосы (11 каналов), гиперпараметры (PATCH_SIZE=256, BATCH_SIZE=8, EPOCHS=100), validate_config() | 219 |
| `models.py` | Архитектура U-Net (conv_block, encoder, decoder, bottleneck), Attention U-Net, U-Net++, data generator с аугментацией, compile_model, predict_full_image (скользящее окно), mc_dropout_predict, реестр моделей | 594 |
| `data_loader.py` | Загрузка с GEE (get_sentinel2, get_landsat, export_year), rasterio (load_image, read_raster_meta), вычисление спектральных индексов | 235 |
| `preprocessing.py` | Растеризация RGI (rasterize_rgi_to_mask), создание патчей (create_patches с stride/balancing), аугментация (augment_patch), train/val/test split, build_dataset | 270 |
| `metrics.py` | Классификационные метрики (F1, Precision, Recall, IoU), pixels_to_area_km2, trend_analysis (линейная регрессия), forecast_to_2050 (95% CI), rmse_against_wgms, ice_volume_loss_to_water_supply | 156 |
| `visualization.py` | RGB композиты, отображение масок, кривые обучения, сетки предсказаний, графики трендов, прогнозов, ежегодные карты ледников | 163 |
| `train.py` | CLI обучение: TrainConfig dataclass, setup_callbacks (ReduceLROnPlateau, EarlyStopping, ModelCheckpoint, TensorBoard), основной цикл | 179 |

#### Архитектуры моделей

| Файл | Архитектуры | Строки |
|------|------------|--------|
| `segmentation_models.py` | FCN, DeepLabV3, PSPNet, LinkNet, SegNet, Attention FPN, HRNet-style. Общий backbone, реестр, оценка сложности | 647 |
| `vision_transformer.py` | Vision Transformer (ViT): patch embedding, multi-head attention, positional encoding, classification head | 617 |
| `diffusion_model.py` | DDPM для супер-решения: forward diffusion, reverse denoising, U-Net backbone, noise schedules | 545 |
| `multi_task_learning.py` | Многозадачная модель: shared encoder + segmentation/classification/regression heads | 408 |
| `graph_neural_network.py` | GNN для связности ледников: message passing, graph convolution, node classification | 427 |

#### Потери и оптимизация

| Файл | Назначение | Строки |
|------|-----------|--------|
| `losses.py` | 10 функций потерь: BCE, weighted BCE, Dice, Focal, Tversky, Lovasz-softmax, boundary-aware, combined, class-weighted, OHEM | 389 |
| `schedulers.py` | LR планировщики: Cosine Annealing, Warmup Cosine/Linear, Exponential/Step/Polynomial Decay, Reduce-on-Plateau, Cyclic/One-Cycle | 495 |
| `hyperparameter_tuning.py` | Grid search, Random search, Bayesian optimization, cross-validation | 698 |
| `model_compression.py` | Квантизация (INT8/FLOAT16), прунинг (structured/unstructured), knowledge distillation | 481 |
| `neural_architecture_search.py` | NAS: search space, weight sharing, performance prediction, evolutionary search | 555 |

#### Обработка данных

| Файл | Назначение | Строки |
|------|-----------|--------|
| `augmentation.py` | Геометрическая (flip, rotate, crop, elastic), фотометрическая (brightness, contrast, gamma, noise), спектральная, MixUp, CutMix, Mosaic, stain normalization | 578 |
| `postprocessing.py` | Морфологические операции, connected components, CRF smoothing, фильтрация шума, уточнение границ | 526 |
| `spectral.py` | Спектральные индексы: NDSI, NDVI, NDWI, MNDWI, BSI, SBI, snow cover, glacier/cloud masks, EVI, NDMI, band math | 816 |
| `feature_engineering.py` | Извлечение признаков: текстура (GLCM), спектральные, пространственные для ML классификаторов | 836 |
| `datasets.py` | Управление датасетами: реестр, обнаружение, валидация, статистика, tf.data.Dataset, патчинг с перекрытием | 686 |

#### Анализ и интерпретация

| Файл | Назначение | Строки |
|------|-----------|--------|
| `evaluation.py` | Пиксельные и региональные метрики, sweep порогов, ROC/PR кривые, матрицы ошибок, batch evaluation, cross-validation | 589 |
| `interpretability.py` | Grad-CAM, attention rollout, occlusion sensitivity, Shapley values, saliency maps, integrated gradients | 849 |
| `anomaly.py` | Isolation forest, pixel-level scoring, z-score/IQR outlier removal, temporal anomaly detection | 610 |
| `clustering.py` | K-means, mini-batch k-means, hierarchical clustering для мультиспектральных изображений | 492 |
| `uncertainty.py` | MC-Dropout inference, ensemble variance, TTA uncertainty, calibration (ECE, MCE, Brier), epistemic vs aleatoric | 599 |

#### Продвинутые техники

| Файл | Назначение | Строки |
|------|-----------|--------|
| `ensemble.py` | Weighted averaging, majority voting, stacking, snapshot ensemble, TTA-enhanced ensemble | 578 |
| `callbacks.py` | MetricsLogger, CheckpointManager, TensorBoardCallback, EarlyStoppingWithRestore, LRSchedulerCallback, UncertaintyCallback | 611 |
| `domain_adaptation.py` | Cross-sensor transfer: band harmonization, histogram matching, pansharpening, spatial resampling | 572 |
| `self_supervised.py` | SimCLR, BYOL, MoCo contrastive learning | 655 |
| `active_learning.py` | Uncertainty/margin/entropy/committee/density/EGL sampling, annotation budget | 469 |
| `federated_learning.py` | FedAvg, differential privacy, adaptive aggregation | 524 |
| `distributed_training.py` | Data/model parallelism, gradient accumulation, weight sync | 493 |

#### Временные ряды и отчёты

| Файл | Назначение | Строки |
|------|-----------|--------|
| `time_series.py` | Mann-Kendall, Sen's slope, change points, seasonal decomposition, anomaly detection, interpolation | 691 |
| `reporting.py` | JSON/CSV/Markdown/HTML отчёты, GeoTIFF metadata, model cards, statistical summaries | 612 |
| `experiment_tracking.py` | Structured lifecycle, dual-backend image I/O, params/metrics/tags tracking | 764 |
| `benchmarking.py` | Inference timing, memory profiling, throughput, latency distribution, FLOPs estimation | 599 |

### 4.5. spaces/ — HuggingFace Spaces

| Файл | Назначение |
|------|-----------|
| `app.py` | Gradio приложение: lazy-загрузка Attention U-Net, спектральные индексы из 7-полосного ввода, инференс скользящим окном, RGB оверлей + карта уверенности |
| `README.md` | Метаданные HuggingFace Spaces |
| `requirements.txt` | gradio>=4.44, tensorflow>=2.15, numpy, rasterio, matplotlib |
| `examples/sample_2020.npy` | Пример ввода: готовый патч Sentinel-2 за 2020 год |

### 4.6. tests/ — 27 тестовых файлов

| Файл | Тестирует |
|------|----------|
| `conftest.py` | Фикстуры: очистка TF MagicMock, rng, sample_image (128x128x11), sample_mask |
| `test_metrics.py` | F1/IoU/Precision/Recall, pixels_to_area, trend_analysis, forecast_to_2050 |
| `test_preprocessing.py` | create_patches, train_val_test_split, augment_patch |
| `test_predict.py` | run_ndsi (форма, бинарный вывод, порог, детерминизм) |
| `test_segmentation_models.py` | Реестр, построение моделей, оценка сложности (mocked TF) |
| `test_config_and_registry.py` | validate_config() и реестр моделей |
| `test_config_validation.py` | Дополнительные тесты валидации конфигурации |
| `test_models_registry.py` | list_models, get_model_info, build_model_by_name |
| `test_benchmarking.py` | Inference timing, throughput, latency (mocked TF) |
| `test_experiment_tracking.py` | ExperimentTracker lifecycle, логирование, запросы |
| `test_hyperparameter_tuning.py` | Grid/random search, Bayesian optimization |
| `test_integration.py` | End-to-end пайплайн сегментации, расчёт площади, синтетический GeoTIFF |
| `test_api_endpoints.py` | /api/models, /api/models/available, /health |
| `test_segmentation_router.py` | POST /api/predict, GET /api/predict/{task_id} |
| `test_compare_router.py` | POST /api/compare |
| `test_history_router.py` | GET /api/history, DELETE /api/history/{task_id} |
| `test_export_router.py` | Экспорт по формату |
| `test_trend_router.py` | POST /api/trend |
| `test_uncertainty_router.py` | POST /api/uncertainty |
| `test_area_service.py` | PIL путь, pixels_to_area |
| `test_llm_service.py` | Маппинг моделей, получение API ключа |
| `test_datasets_router.py` | CRUD, создание, валидация, samples, stats |
| `test_tasks_router.py` | CRUD, список, отмена, пагинация |
| `test_training_router.py` | start, status, stop, resume, history, models, config |
| `test_monitoring_router.py` | MetricsCollector, health checker, system info |
| `test_ws_router.py` | ConnectionManager: connect, disconnect, broadcast, rooms |

### 4.7. notebooks/ — 12 файлов

| Файл | Назначение |
|------|-----------|
| `README.md` | Руководство по выполнению: prerequisites, порядок (01-06), длительность |
| `01_data_download.ipynb` | Загрузка данных с GEE: Sentinel-2, Landsat, RGI контуры |
| `01_data_download_executed.ipynb` | Выполненная версия notebook 01 |
| `02_preprocessing.ipynb` | Создание масок, генерация патчей, train/val/test split |
| `03_baseline_models.ipynb` | NDSI threshold, Random Forest, сравнение базовых моделей |
| `04_unet_training.ipynb` | Обучение U-Net с настройкой гиперпараметров |
| `05_temporal_analysis.ipynb` | Многолетний анализ, тренд, прогноз до 2050, валидация WGMS |
| `06_visualization.ipynb` | Финальные карты и фигуры для статьи |
| `_generate_notebooks.py` | Python генератор .ipynb файлов из кода (669 строк) |
| `_synthetic_smoke_test.py` | End-to-end тест пайплайна на синтетических данных (без TF) |
| `_unet_smoke_test.py` | Smoke test U-Net: build, train 2 эпохи, инференс, MC-Dropout |

### 4.8. docs/ — 8 документов

| Файл | Назначение |
|------|-----------|
| `ARCHITECTURE.md` | Архитектура системы: 3-tier диаграмма, middleware, auth, routing, ML пайплайн, Docker, безопасность, CI/CD. 591 строка |
| `API_REFERENCE.md` | Полный API: все эндпоинты, auth, request/response схемы. 775 строк |
| `literature_review.md` | 14 источников литературы с DOI, ключевые датасеты, статистика |
| `DECISIONS.md` | Лог архитектурных решений: D-001 (RF для временных рядов), D-002 (линейный прогноз), D-003 (Attention U-Net), ... |
| `checklist.md` | 66 пунктов чек-листа по месяцам |
| `contacts_and_partnerships.md` | 5 потенциальных партнёров: WGMS, КазНАН, КазНУ, ЦАГЦ, Константин Маслов |
| `CONTRIBUTING.md` | Руководство по вкладу (дублирование) |
| `GITHUB_ISSUES.md` | 5 готовых GitHub issues |

### 4.9. paper/ — Научная статья

| Файл | Назначение |
|------|-----------|
| `draft_outline.md` | 8-секционная структура: Introduction, Literature Review, Methods, Results, Discussion, Conclusion, References, Appendix |
| `methodology.md` | Детальная методология: район исследования, источники данных, preprocessing, U-Net, базовые модели, метрики |
| `results_template.md` | Шаблон результатов: таблица сравнения моделей, временной ряд площади (2000-2020), тренд, прогноз до 2050 |

### 4.10. Остальные директории

| Директория | Содержимое |
|------------|-----------|
| `scripts/generate_figures.py` | Генерация всех фигур для статьи: тренд+прогноз, карты по годам, сравнение моделей, кривые обучения |
| `scripts/validate-env.py` | Валидатор окружения: Docker, Python, Node.js, pip пакеты, .env файлы |
| `models/` | `unet_best.h5`, `attention_unet_best.h5`, `random_forest.pkl` |
| `results/figures/` | 7 PNG фигур, `results/tables/` — 2 CSV, `results/masks/`, `results/tensorboard/`, `results/training_log.csv` |
| `predictions/` | 9 директорий по годам (2000, 2003, 2005, 2008, 2010, 2013, 2016, 2017, 2020) |
| `data/raw/sentinel2/` | Sentinel-2 GeoTIFF композиты |
| `data/raw/landsat/` | Landsat GeoTIFF композиты |
| `data/processed/masks/` | Маски ледников по годам |
| `data/processed/patches/` | Патчи для обучения (.npy, только 2020) |
| `data/rgi/` | RGI 7.0 shapefiles |
| `plans/MASTER_PLAN.md` | 562-строчный план: 5 фаз с задачами и критериями верификации |
| `.github/workflows/ci.yml` | CI: lint (ruff) + test (pytest) + typecheck (pyright) + frontend-test (vitest) + security (bandit/safety) + docker-build |

---

## 5. Пайплайн обработки данных

### 5.1. Загрузка (notebook 01)

```
Google Earth Engine → Sentinel-2 L2A (2015-2024) / Landsat (2000-2013)
→ Compositing по годам → GeoTIFF (B2,B3,B4,B8,B8A,B11,B12)
```

### 5.2. Предобработка (notebook 02)

```
GeoTIFF + RGI Shapefile → Растеризация масок → Нормализация бандов
→ Создание патчей 256×256 (stride=128) → Аугментация (flip, rotate, brightness)
→ Train/Val/Test split (70/15/15) → .npy файлы
```

### 5.3. Обучение (notebook 04)

```
.npy патчи → tf.data.Dataset → U-Net / Attention U-Net
→ Adam 1e-4, batch=8, 100 эпох
→ ReduceLROnPlateau + EarlyStopping(patience=15) + TensorBoard
→ Лучшая модель → .h5 веса
```

### 5.4. Инференс

```
GeoTIFF → Загрузка бандов → Спектральные индексы (NDSI, NDWI, BSI, EVI)
→ Паддинг до кратного 256 → Скользящее окно (step=128, 50% overlap)
→ TTA: 3 отражения (horizontal, vertical, both)
→ MC-Dropout: N forward passes → mean + std + entropy
→ Порог 0.5 → бинарная маска ледника
→ Расчёт площади: pixels × 10m × 10m → км²
```

### 5.5. Временной ряд (notebook 05)

```
Маски по годам (2000-2020) → Расчёт площади по годам
→ Линейная регрессия (scipy.stats.linregress)
→ Прогноз до 2050 с 95% доверительным интервалом
→ Сравнение с WGMS данными (RMSE)
→ Расчёт потерь объёма льда → водоснабжение
```

---

## 6. Модели машинного обучения

### 6.1. Основные модели

| Модель | Описание | F1 | IoU |
|--------|----------|-----|-----|
| U-Net | Классический encoder-decoder с skip connections | 0.862 | 0.758 |
| **Attention U-Net** | **U-Net + attention gates** | **0.876** | **0.779** |
| U-Net++ | Dense skip connections | 0.871 | 0.772 |
| Random Forest | Pixel-wise классификатор на спектральных признаках | 0.798 | 0.664 |
| NDSI | Пороговый метод (NDSI > 0.4) | 0.756 | 0.608 |
| Ансамбль | Взвешенное усреднение 5 моделей | 0.874 | 0.776 |

### 6.2. Архитектура Attention U-Net

```
Input (256×256×11)
├── Encoder Block 1: Conv(64) → BN → ReLU → Conv(64) → BN → ReLU
├── MaxPool(2)
├── Encoder Block 2: Conv(128) → BN → ReLU → Conv(128) → BN → ReLU
├── MaxPool(2)
├── Encoder Block 3: Conv(256) → BN → ReLU → Conv(256) → BN → ReLU
├── MaxPool(2)
├── Encoder Block 4: Conv(512) → BN → ReLU → Conv(512) → BN → ReLU
├── MaxPool(2)
├── Bottleneck: Conv(1024) → BN → ReLU → Conv(1024) → BN → ReLU
├── UpConv(512) + Attention Gate + Concat(Enc4)
├── Decoder Block: Conv(512) → BN → ReLU → Conv(512) → BN → ReLU
├── UpConv(256) + Attention Gate + Concat(Enc3)
├── Decoder Block: Conv(256) → BN → ReLU → Conv(256) → BN → ReLU
├── UpConv(128) + Attention Gate + Concat(Enc2)
├── Decoder Block: Conv(128) → BN → ReLU → Conv(128) → BN → ReLU
├── UpConv(64) + Attention Gate + Concat(Enc1)
├── Decoder Block: Conv(64) → BN → ReLU → Conv(64) → BN → ReLU
└── Conv(1) → Sigmoid → Output (256×256×1)
```

### 6.3. Спектральные каналы (11)

| # | Канал | Описание |
|---|-------|----------|
| 1 | B2 | Blue (490nm) |
| 2 | B3 | Green (560nm) |
| 3 | B4 | Red (665nm) |
| 4 | B8 | NIR (842nm) |
| 5 | B8A | NIR narrow (865nm) |
| 6 | B11 | SWIR1 (1610nm) |
| 7 | B12 | SWIR2 (2190nm) |
| 8 | NDSI | Normalized Difference Snow Index = (Green - SWIR1) / (Green + SWIR1) |
| 9 | NDWI | Normalized Difference Water Index = (Green - NIR) / (Green + NIR) |
| 10 | BSI | Bare Soil Index = (SWIR1 - Red) / (SWIR1 + Red) |
| 11 | EVI | Enhanced Vegetation Index = 2.5 × (NIR - Red) / (NIR + 6×Red - 7.5×Blue + 1) |

---

## 7. API эндпоинты

### Основные

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/predict` | Загрузка изображения → сегментация |
| `GET` | `/api/predict/{task_id}` | Получение результата сегментации |
| `POST` | `/api/compare` | Сравнение нескольких моделей |
| `POST` | `/api/area` | Расчёт площади из маски |
| `GET` | `/api/history` | История сегментаций |
| `DELETE` | `/api/history/{task_id}` | Удаление из истории |
| `GET` | `/api/export/{task_id}` | Экспорт маски |
| `GET` | `/api/export/{task_id}/stats` | Статистика экспорта |
| `POST` | `/api/trend` | Анализ тренда |
| `POST` | `/api/uncertainty` | Оценка неопределённости |
| `GET` | `/api/models` | Список моделей |
| `GET` | `/api/models/available` | Доступные модели |
| `POST` | `/api/analysis/analyze` | LLM анализ |
| `GET` | `/api/analysis/models` | LLM провайдеры |

### Администрирование

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/admin/status` | Статус системы |
| `GET` | `/api/admin/config` | Конфигурация |
| `PUT` | `/api/admin/config` | Обновление конфигурации |
| `GET` | `/api/admin/users` | Список пользователей |
| `POST` | `/api/admin/users` | Создание пользователя |
| `DELETE` | `/api/admin/users/{user_id}` | Удаление пользователя |
| `GET` | `/api/admin/audit` | Аудит лог |
| `GET` | `/api/admin/logs` | Системные логи |

### Отчёты

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/reports/training/latest` | Последний отчёт обучения |
| `GET` | `/api/reports/inference/latest` | Последний отчёт инференса |
| `GET` | `/api/reports/summary/daily` | Дневная сводка |
| `GET` | `/api/reports/{report_id}` | Отчёт по ID |
| `DELETE` | `/api/reports/{report_id}` | Удаление отчёта |
| `POST` | `/api/reports/export/{report_id}` | Экспорт отчёта |

---

## 8. Фронтенд

### 8.1. Навигация (10 секций)

1. **Dashboard** — Обзор с метриками
2. **Predict** — Сегментация нового изображения
3. **Compare** — Сравнение моделей
4. **Trend** — Анализ трендов
5. **Datasets** — Управление датасетами
6. **Training** — Обучение моделей
7. **Reports** — Отчёты
8. **History** — История
9. **Analysis** — AI анализ (LLM)
10. **Settings** — Настройки

### 8.2. Языки

- **English** (en) — основной
- **Русский** (ru) — полный перевод
- **Қазақша** (kk) — казахский

### 8.3. Технологии

- **React 19** + **Next.js 16** (App Router)
- **Tailwind CSS 4** — стилизация
- **Leaflet** — карты
- **Recharts** — графики
- **lucide-react** — иконки
- **react-dropzone** — drag-and-drop загрузка
- **jspdf** — PDF экспорт

---

## 9. Инфраструктура и DevOps

### 9.1. Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports: 6379
    healthcheck: redis-cli ping

  api:
    build: glacierkz-api/
    ports: 8000
    depends_on: redis
    healthcheck: curl http://localhost:8000/health
    resources:
      limits: memory 4G

  web:
    build: glacierkz-web/
    ports: 3000
    depends_on: api
    healthcheck: curl http://localhost:3000
```

### 9.2. CI/CD (GitHub Actions)

| Job | Инструменты | Описание |
|-----|------------|----------|
| lint | ruff | Проверка стиля кода |
| test | pytest + coverage | 322 теста с покрытием |
| typecheck | pyright | Статическая типизация |
| frontend-test | vitest + next build | Тесты фронтенда |
| security | bandit + safety | Безопасность зависимостей |
| docker-build | docker build | Сборка образов api + web |

### 9.3. Безопасность

- `.env` файлы в `.gitignore`
- API Key аутентификация (SHA-256)
- JWT токены (HS256/RS256)
- RBAC (Viewer/Analyst/Admin)
- Rate limiting (token bucket)
- Security headers (CSP, HSTS, X-Frame-Options)
- CORS настройки
- Максимальный размер файла: 200 MB

---

## 10. Тестирование

### 10.1. Статистика

| Метрика | Значение |
|---------|----------|
| Всего тестов | 322 |
| Python тесты | 27 файлов |
| Frontend тесты | 14 файлов |
| Статус | Все проходят (0 failed) |
| Покрытие | HTML отчёт в `htmlcov/` |

### 10.2. Запуск тестов

```bash
# Python тесты
pytest tests/ -v

# Frontend тесты
cd glacierkz-web && npm test

# Всё вместе
ruff check . && pytest tests/ -v && cd glacierkz-web && npm test
```

---

## 11. Roadmap

### 11.1. Фазы проекта

| Фаза | Описание | Статус |
|------|----------|--------|
| 1 | Инфраструктура (Docker, API, Web) | ✅ Завершена |
| 2 | Данные (GEE загрузка, preprocessing) | ✅ Завершена |
| 3 | Baseline модели (NDSI, RF) | ✅ Завершена |
| 4 | U-Net обучение | ✅ Завершена |
| 5 | Temporal анализ + прогноз | ✅ Завершена |
| 6 | Веб-интерфейс + API | ✅ Завершена |
| 7 | Тестирование + CI/CD | ✅ Завершена |
| 8 | Документация + статья | ✅ Завершена |
| 9 | Запуск на реальных данных (2000-2020) | 🔄 В процессе |
| 10 | Публичная версия и пилоты | 📋 Запланировано |

### 11.2. Рекомендации по дальнейшим шагам

1. Запустить полный пайплайн на реальных данных Sentinel-2/Landsat (2000–2020)
2. Обучить модель Attention U-Net на полном наборе данных
3. Завершить notebooks 03–06 с реальными результатами → заполнить плейсхолдеры X/Y/Z в статье
4. Обработать все годы через `seed_db.py` для полной БД истории
5. Обеспечить потокобезопасность `_MODEL_CACHE` при переходе на production concurrency
