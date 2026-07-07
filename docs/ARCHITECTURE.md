# Architecture

> System design, component breakdown, and data flow for GlacierNET-KZ.
> See also: [`API_REFERENCE.md`](./API_REFERENCE.md) | [`CONTRIBUTING.md`](./CONTRIBUTING.md)

## Table of Contents

- [Overview](#overview)
- [System Diagram](#system-diagram)
- [Technology Stack](#technology-stack)
- [Backend (FastAPI)](#backend-fastapi)
  - [Middleware Stack](#middleware-stack)
  - [Authentication & Authorization](#authentication--authorization)
  - [Routing Layer](#routing-layer)
  - [Core Services](#core-services)
  - [WebSocket Layer](#websocket-layer)
  - [Monitoring](#monitoring)
- [Frontend (Next.js)](#frontend-nextjs)
  - [Page Routes](#page-routes)
  - [UI Components](#ui-components)
  - [State Management](#state-management)
  - [Internationalization](#internationalization)
- [Machine Learning Pipeline](#machine-learning-pipeline)
  - [Model Architecture](#model-architecture)
  - [Inference Pipeline](#inference-pipeline)
  - [Training Pipeline](#training-pipeline)
  - [Prediction Flow](#prediction-flow)
- [Data Layer](#data-layer)
  - [Satellite Data](#satellite-data)
  - [Task State Machine](#task-state-machine)
  - [Results Storage](#results-storage)
- [MCP Server](#mcp-server)
- [Infrastructure](#infrastructure)
  - [Docker Compose](#docker-compose)
  - [Networking](#networking)
  - [Volume Layout](#volume-layout)
- [Security](#security)
- [CI/CD](#cicd)

---

## Overview

GlacierNET-KZ is a three-tier application:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │───▶│    API      │───▶│  ML Engine  │
│  (Next.js)  │    │  (FastAPI)  │    │  (TF/Keras) │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │    MCP      │
                   │   Server    │
                   └─────────────┘
```

- **Frontend:** Next.js 16 React app with Leaflet maps, Recharts visualizations, and React Context for i18n (en/ru/kk).
- **API:** FastAPI with JWT/API-key auth, RBAC, rate limiting, CORS, and WebSocket pub/sub.
- **ML Engine:** TensorFlow/Keras U-Net, Attention U-Net, U-Net++, scikit-learn Random Forest, OpenCV-based NDSI thresholding.
- **MCP Server:** Model Context Protocol tool server exposing satellite data to LLM clients.

---

## System Diagram

```
Browser / Desktop
       │
       │ HTTPS
       ▼
┌──────────────────────────────────────────────────┐
│                   Next.js Frontend               │
│  ┌──────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ │
│  │ Pages│ │Components│ │  lib/  │ │  store/   │ │
│  └──┬───┘ └────┬─────┘ └───┬────┘ └─────┬─────┘ │
│     └──────────┴────────────┴────────────┘       │
└──────────────────────┬───────────────────────────┘
                       │ /api/*
┌──────────────────────▼───────────────────────────┐
│                  FastAPI Backend                  │
│  ┌─────────────────────────────────────────────┐  │
│  │              Middleware Pipeline            │  │
│  │  SecurityHeaders→RequestLogging→RateLimit   │  │
│  │  →Cache→CORS                               │  │
│  └──────────────────┬──────────────────────────┘  │
│  ┌──────────┬───────▼───────┬──────────────────┐  │
│  │ Routers  │    Routes     │   WebSocket      │  │
│  │ seg/comp/│  tasks/ds/    │  /ws/{id}        │  │
│  │ trend/   │  train/mon    │  ConnectionMgr   │  │
│  │ export/  │               │  Room pub/sub    │  │
│  │ history  │               │                  │  │
│  └────┬─────┴───────┬───────┴──────────────────┘  │
│       │             │                             │
│  ┌────▼─────┐  ┌────▼─────────────────────────┐   │
│  │ Auth     │  │     Core Services             │   │
│  │ API Key  │  │  SegmentationService          │   │
│  │ JWT      │  │  CompareService               │   │
│  │ RBAC     │  │  TrendService                 │   │
│  └──────────┘  │  ExportService                │   │
│                │  HistoryService                │   │
│                │  HealthChecker                 │   │
│                │  MetricsCollector              │   │
│                └───────────┬───────────────────┘   │
└────────────────────────────┼──────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   ML Pipeline   │
                    │  ┌───────────┐  │
                    │  │   UNet    │  │
                    │  │ AttnUNet  │  │
                    │  │  RF/NDSI  │  │
                    │  └─────┬─────┘  │
                    │        │        │
                    │  ┌─────▼─────┐  │
                    │  │ Inference  │  │
                    │  │ PostProc   │  │
                    │  │ Metrics    │  │
                    │  └───────────┘  │
                    └─────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16, React 19 | SSR/CSR UI framework |
| State | Zustand | Lightweight client-side store |
| Maps | Leaflet + react-leaflet | Glacier boundary visualization |
| Charts | Recharts | Area charts, time series |
| Uploads | react-dropzone | File upload component |
| Backend | FastAPI (Python 3.10+) | REST API + WebSocket |
| Auth | PyJWT (HS256/RS256) | Token-based authentication |
| Rate limiting | Token bucket (in-memory or Redis) | API abuse prevention |
| ML | TensorFlow/Keras, scikit-learn, OpenCV | Glacier segmentation |
| LLM | Ollama (local), OpenAI (cloud) | AI-assisted analysis |
| Database | SQLite (task tracking, history) | Structured persistence |
| Storage | Filesystem (`RESULTS_DIR`) | GeoTIFF masks, overlays |
| MCP | Model Context Protocol (stdio/SSE) | LLM tool integration |
| Infra | Docker Compose | Multi-service deployment |
| Monitoring | Prometheus metrics, health endpoints | Observability |

---

## Backend (FastAPI)

Entry point: `glacierkz-api/app/main.py`

```python
# Simplified initialization flow
app = FastAPI(title="GlacierNET-KZ API", ...)
# Middleware (order matters — last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, ...)
app.add_middleware(CacheMiddleware, ...)
app.add_middleware(CORSMiddleware, ...)
# Routers
app.include_router(segmentation_router)
app.include_router(compare_router)
app.include_router(export_router)
app.include_router(history_router)
app.include_router(trend_router)
app.include_router(tasks_router)
app.include_router(datasets_router)
app.include_router(training_router)
app.include_router(monitoring_router)
# WebSocket
app.add_api_websocket_route("/ws/{client_id}", ws_handler)
```

### Middleware Stack

Applied in reverse order (outermost first):

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 1 | SecurityHeaders | CSP, HSTS, X-Frame-Options |
| 2 | RequestLogging | Structured access logs with timing |
| 3 | RateLimit | Token-bucket per-IP throttling |
| 4 | Cache | Response caching (conditional) |
| 5 | CORS | Cross-origin origin control |

### Authentication & Authorization

**Three layers:**

1. **API Key** (`app/auth/api_key.py`): SHA-256 hashed key comparison from `X-API-Key` header or `?api_key=` query param. Keys loaded from `app/permissions/api_keys.json`.

2. **JWT** (`app/auth/jwt_auth.py`): Bearer token in `Authorization` header. Supports HS256 (symmetric secret) and RS256 (public/private key). Token payload carries `sub`, `role`, `scopes`.

3. **RBAC** (`app/auth/rbac.py`): `require_role(minimum_role)` FastAPI dependency. Three roles:
   - `viewer` (level 0) — read-only
   - `analyst` (level 1) — run predictions and analyses
   - `admin` (level 2) — training, datasets, user management

### Routing Layer

Routes are split across two packages:

**`app/routers/`** — Domain-specific prediction endpoints:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `segmentation` | `/api/predict` | `POST` run prediction, `GET {task_id}` poll |
| `compare` | `/api/compare` | `POST` multi-model comparison |
| `trend` | `/api/trend` | `POST` time series analysis |
| `export` | `/api/export` | `GET {task_id}` download |
| `history` | `/api/history` | `GET` list, `DELETE {task_id}` remove |

**`app/routes/`** — Operational management endpoints:

| Route | Prefix | Endpoints |
|-------|--------|-----------|
| `tasks` | `/api/tasks` | `POST create`, `GET {id}`, `POST {id}/cancel`, `GET active`, `GET /` |
| `datasets` | `/api/datasets` | `GET /`, `POST create`, `GET/DELETE {id}`, `POST {id}/upload`, `GET {id}/validate|samples|stats` |
| `training` | `/api/training` | `POST start`, `GET status`, `POST stop/resume`, `GET history|models|config`, `DELETE models/{id}` |
| `monitoring` | `/api/monitoring` | `GET metrics|system|status` |

### Core Services

Located in `app/services/`:

- **`SegmentationService`** — Loads model, runs inference, applies post-processing (TTA, CRF), computes area metrics, saves mask/overlay files.
- **`CompareService`** — Runs segmentation across multiple models in parallel, collects results into a comparison array.
- **`TrendService`** — Takes historical area measurements, fits linear regression, computes forecast with confidence intervals, calculates loss rates and significance.
- **`ExportService`** — Generates output in JSON, GeoJSON, or CSV formats from stored results.
- **`HistoryService`** — CRUD operations on the prediction history database.

### WebSocket Layer

- **`ConnectionManager`** (`app/ws/manager.py`): Manages client connections, room-based pub/sub, heartbeat loop (30s ping, 60s timeout).
- **Handler** (`app/ws/handlers.py`): Processes `ping`, `join_room`, `leave_room`, `broadcast`, `stats` messages.

### Monitoring

- **`HealthChecker`** (`app/monitoring/health.py`): Liveness (`/livez`), readiness (`/readyz`), and deep health checks. Validates disk space, CPU, memory thresholds.
- **`MetricsCollector`** (`app/monitoring/`): Prometheus-format metrics — uptime, CPU, memory, open FDs, thread count.
- **Monitoring routes** (`app/routes/monitoring.py`): `/api/monitoring/metrics` (Prometheus), `/system` (detailed JSON), `/status` (lightweight liveness).

---

## Frontend (Next.js)

Entry point: `glacierkz-web/src/app/layout.tsx`

### Page Routes

| Path | Page | Description |
|------|------|-------------|
| `/` | `page.tsx` | Landing page |
| `/analysis` | `analysis/page.tsx` | Start new segmentation |
| `/compare` | `compare/page.tsx` | Multi-model comparison |
| `/dashboard` | `dashboard/page.tsx` | Overview with charts |
| `/datasets` | `datasets/page.tsx` | Dataset management |
| `/history` | `history/page.tsx` | Past prediction results |
| `/predict` | `predict/page.tsx` | Single-model prediction |
| `/reports` | `reports/page.tsx` | Generate reports |
| `/settings` | `settings/page.tsx` | App configuration |
| `/training` | `training/page.tsx` | Model training UI |
| `/trend` | `trend/page.tsx` | Time series analysis |

### UI Components

Located in `src/components/`:

| Component | Purpose |
|-----------|---------|
| `Navbar.tsx` | Top navigation with route links |
| `FileUpload.tsx` | react-dropzone wrapper for GeoTIFF upload |
| `MapViewer.tsx` | Leaflet map for glacier boundary display |
| `ResultsChart.tsx` | Recharts area/bar chart for area stats |
| `TimeSeriesChart.tsx` | Recharts line chart for temporal trends |
| `ModelSelector.tsx` | Model selection dropdown |
| `ComparisonGrid.tsx` | Side-by-side multi-model results |
| `ProgressIndicator.tsx` | Task progress bar/spinner |
| `TaskStatus.tsx` | Task state badge and status text |
| `LLMAnalysis.tsx` | LLM chat interface for analysis |
| `HistoryCard.tsx` | Card for a single history record |
| `ExportButton.tsx` | Format selector + download trigger |
| `LanguageSwitcher.tsx` | RU/EN locale toggle |
| `Toast.tsx` | Notification toast component |

### State Management

Client state uses React hooks (`useState`, `useCallback`, `useEffect`) and a custom `I18nProvider` context in `src/lib/I18nProvider.tsx`. Locale preference is persisted in `localStorage` under `glacierkz-locale`. No global store library (Redux/Zustand) is required for the current scope.

### Internationalization

i18n module at `src/lib/i18n.ts` with **en**, **ru**, and **kk** locale objects (~340 keys each). All UI text is referenced via `useI18n().t("key")`. The active locale syncs to `<html lang>` via `HtmlLangSync`.

---

## Machine Learning Pipeline

### Model Architecture

| Model | Framework | Input Shape | Description |
|-------|-----------|-------------|-------------|
| UNet | TensorFlow/Keras | `(H, W, C)` | Encoder-decoder with skip connections |
| Attention UNet | TensorFlow/Keras | `(H, W, C)` | UNet with attention gates |
| U-Net++ | TensorFlow/Keras | `(H, W, C)` | Nested U-Net with dense skip connections |
| Random Forest | scikit-learn | `(N, features)` | Pixel-level ensemble classifier |
| NDSI | NumPy/rasterio | `(H, W)` | Normalized Difference Snow Index thresholding |

### Inference Pipeline

```
Input GeoTIFF
    │
    ▼
┌──────────────────┐
│ Load & Preprocess │  → band extraction, normalization, tiling
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Model Inference  │  → per-pixel probability map
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Post-Process   │  → thresholding, optional TTA, optional CRF
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Compute Area   │  → pixel count × pixel area → km²
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Save Outputs    │  → mask PNG, overlay PNG, metadata JSON
└──────────────────┘
```

### Training Pipeline

```
┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│   Dataset    │────▶│  Data Loader   │────▶│   Trainer    │
│  (GeoTIFFs)  │     │  (augment,     │     │  (epochs,    │
│              │     │   normalize)   │     │   validation)│
└──────────────┘     └────────────────┘     └──────┬───────┘
                                                    │
                                           ┌────────▼───────┐
                                           │  Checkpoints   │
                                           │  + Metrics     │
                                           └────────────────┘
```

### Prediction Flow

1. User uploads GeoTIFF via `FileUpload` component
2. Frontend calls `POST /api/predict` with file + model config
3. API creates task, returns `task_id`
4. Frontend opens WebSocket, subscribes to task updates
5. `SegmentationService` runs inference, posts progress via WebSocket
6. On completion, frontend receives result with `area_km2`, overlay paths
7. `MapViewer` renders the mask overlay on Leaflet

---

## Data Layer

### Satellite Data

Stored in `satellite_data/` under the project root:

```
satellite_data/
├── 2000/
│   ├── band1.tif
│   ├── band2.tif
│   └── ...
├── 2003/
│   └── ...
├── 2010/
│   └── ...
├── 2020/
│   └── ...
└── metadata/
    └── years.json
```

Years with data: `2000, 2003, 2006, 2009, 2011, 2013, 2016, 2017, 2020`

### Task State Machine

```
                    ┌──────────┐
                    │  pending │
                    └────┬─────┘
                         │ start
                         ▼
                    ┌──────────┐
              ┌─────│ running  │─────┐
              │     └──────────┘     │
              │                      │
         ┌────▼─────┐         ┌─────▼──────┐
         │completed │         │  failed    │
         └──────────┘         └────────────┘
                                  │
                             ┌────▼─────┐
                             │cancelled │
                             └──────────┘
```

Transitions:
- `pending → running` — worker picks up the task
- `running → completed` — inference/train finishes successfully
- `running → failed` — exception during processing
- `pending | running → cancelled` — user cancellation via `POST /api/tasks/{id}/cancel`

### Results Storage

All outputs written to `RESULTS_DIR` (configurable via env):

```
results/
├── {task_id}/
│   ├── input.tif          # original uploaded image
│   ├── mask.png           # binary glacier mask
│   ├── overlay.png        # colored overlay on original
│   ├── thumb.png          # thumbnail for history list
│   └── metadata.json      # area_km2, model_name, timestamps
└── compare/
    └── {task_id}/
        ├── unet_mask.png
        ├── unet_overlay.png
        ├── rf_mask.png
        └── rf_overlay.png
```

---

## MCP Server

Entry point: `glacierkz-mcp/server.py`

The MCP server provides a bridge between LLM clients and the satellite data layer. It reads directly from the `satellite_data/` directory and computed result files.

**Transport modes:**
- **stdio** (default): LLM client spawns the server as a subprocess
- **SSE** (optional): HTTP server mode with `--sse` flag

**Tool categories:**
1. **Data discovery:** `list_data_years`, `get_available_models`, `get_study_area_info`
2. **Area analysis:** `get_glacier_area`, `get_all_glacier_areas`
3. **Time series:** `get_glacier_time_series`
4. **Spatial queries:** `query_pixel`, `get_band_statistics`
5. **Metadata:** `get_image_metadata`

---

## Infrastructure

### Docker Compose

Three services on the `backend` network:

| Service | Image | Port | Memory | Healthcheck |
|---------|-------|------|--------|-------------|
| Redis | `redis:7-alpine` | 6379 | 256 MB | `redis-cli ping` |
| API | `glacierkz-api` | 8000 | 2 GB | `curl /health` |
| Web | `glacierkz-web` | 3000 | 512 MB | `curl localhost:3000` |

```yaml
# Simplified compose structure
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    deploy: { resources: { limits: { memory: 256M } } }
    healthcheck: { test: ["CMD", "redis-cli", "ping"] }

  api:
    build: ./glacierkz-api
    ports: ["8000:8000"]
    depends_on: { redis: { condition: service_healthy } }
    deploy: { resources: { limits: { memory: 2G } } }
    environment:
      - REDIS_URL=redis://redis:6379
      - API_KEYS_FILE=/app/permissions/api_keys.json

  web:
    build: ./glacierkz-web
    ports: ["3000:3000"]
    depends_on: [api]
    deploy: { resources: { limits: { memory: 512M } } }

networks:
  backend:
    driver: bridge
```

### Networking

```
Internet ──▶ :3000 (Web/Nginx) ──▶ /api/* ──▶ :8000 (FastAPI)
                                           ──▶ /ws/*  ──▶ :8000 (WebSocket)
                                   :6379 ◀── FastAPI (Redis, optional)
```

### Volume Layout

```
./
├── glacierkz-api/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── auth/
│   │   ├── routes/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── schemas/
│   │   ├── middleware/
│   │   ├── monitoring/
│   │   └── ws/
│   ├── tests/
│   └── Dockerfile
├── glacierkz-web/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── store/
│   ├── package.json
│   └── Dockerfile
├── glacierkz-mcp/
│   ├── server.py
│   └── README.md
├── satellite_data/
├── results/
├── docker-compose.yml
└── pyproject.toml
```

---

## Security

| Control | Implementation |
|---------|---------------|
| API authentication | API key (header/query) + JWT bearer token |
| Authorization | RBAC with 3 roles: viewer(0), analyst(1), admin(2) |
| Rate limiting | Token-bucket per IP, 60 req/min, 1000 req/hr, burst 10 |
| CORS | Configurable allowed origins via `CORS_ORIGINS` env |
| Security headers | CSP, HSTS (1 year), X-Frame-Options: DENY, X-Content-Type-Options: nosniff |
| Secrets | API keys and JWT secrets stored in env vars, never in code |
| Input validation | Pydantic models for all request/response schemas |
| File uploads | Size limits, format validation (GeoTIFF only) |
| HTTPS | Terminated at reverse proxy (Nginx/Caddy), not at FastAPI |
| WebSocket auth | Client ID in URL path; room-based isolation |

---

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push/PR to `main`:

| Job | Tool | Scope |
|-----|------|-------|
| lint | Ruff | `src/`, `glacierkz-api/app/` |
| test | pytest + pytest-cov | `tests/`, `glacierkz-api/tests/` (coverage ≥ 25%) |
| typecheck | Pyright | `glacierkz-api/app/` |
| frontend-test | Vitest + ESLint + `next build` | `glacierkz-web/` |
| e2e | Playwright (web + API) | `glacierkz-web/e2e/` |
| security | Bandit + Safety | Python dependencies |
| validate | `scripts/validate-env.py` | Environment schema |
| docker-build | Docker | API + Web images |

To run locally:

```bash
# Lint
ruff check src/ glacierkz-api/app/
ruff format src/ glacierkz-api/app/ --check

# Test (full suite)
python -m pytest tests/ glacierkz-api/tests/ -v

# Type check
pyright

# Frontend
cd glacierkz-web && npm run lint && npm test && npm run build
```
