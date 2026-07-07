# API Reference

> GlacierNET-KZ REST API, WebSocket, and MCP tool reference.
> Base URL: `http://localhost:8000`

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Responses](#error-responses)
- [Segmentation](#segmentation)
- [Model Comparison](#model-comparison)
- [Temporal Trend](#temporal-trend)
- [Export](#export)
- [History](#history)
- [Task Management](#task-management)
- [Dataset Management](#dataset-management)
- [Training](#training)
- [Monitoring](#monitoring)
- [LLM Analysis](#llm-analysis)
- [WebSocket](#websocket)
- [MCP Tools](#mcp-tools)

---

## Authentication

The API supports three authentication mechanisms. All protected endpoints require at least one.

### API Key (Header or Query)

Include the key via header **or** query parameter:

```
X-API-Key: your-api-key-here
```
```
GET /api/history?api_key=your-api-key-here
```

Keys are SHA-256 hashed before comparison. The key file is loaded from `API_KEYS_FILE` (default `app/permissions/api_keys.json`).

### JWT Bearer Token

```
Authorization: Bearer <access_token>
```

Tokens are signed with HS256 (symmetric) or RS256 (asymmetric). Obtain tokens via the auth endpoints (not documented here — internal use). Token payload structure:

```json
{
  "sub": "user-id",
  "role": "analyst",
  "scopes": ["read", "predict"],
  "exp": 1700000000,
  "iat": 1699996400
}
```

### Role-Based Access Control

Three roles with increasing privilege:

| Role      | Level | Capabilities |
|-----------|-------|-------------|
| `viewer`  | 0     | Read-only access to results and history |
| `analyst` | 1     | Run predictions, comparisons, trend analysis |
| `admin`   | 2     | All above + training, dataset management, user admin |

Protected routes use `require_role(RoleLevel)` as a FastAPI dependency.

---

## Rate Limiting

Token-bucket algorithm with per-client tracking via IP (or `X-Forwarded-For`).

| Parameter | Default |
|-----------|---------|
| Burst size | 10 requests |
| Requests/minute | 60 |
| Requests/hour | 1000 |

**Exempt paths:** `/health`, `/docs`, `/openapi.json`

**Response headers on every request:**

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
```

**429 response:**

```json
{
  "detail": "Rate limit exceeded"
}
```

```
Retry-After: 3
```

---

## Error Responses

All error responses follow the FastAPI convention:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request / validation error |
| 401 | Missing or invalid authentication |
| 403 | Insufficient role/permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g. cancelling a completed task) |
| 413 | File too large (prediction upload) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Segmentation

### `POST /api/predict`

Run glacier segmentation on a satellite image.

**Auth:** `analyst`+ | **Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | GeoTIFF satellite image |
| `model_name` | string | yes | `unet`, `attention_unet`, `random_forest`, `ndsi` |
| `use_tta` | boolean | no | Test-time augmentation (3 flips). Default `false` |
| `use_crf` | boolean | no | CRF post-processing. Default `false` |
| `ndsi_threshold` | float | no | Override NDSI threshold (0–1) |

**Response `200`:**

```json
{
  "task_id": "abc123def456",
  "status": "completed",
  "mask_path": "/results/abc123/mask.png",
  "overlay_path": "/results/abc123/overlay.png",
  "area_km2": 1.234,
  "model_name": "unet"
}
```

### `GET /api/predict/{task_id}`

Poll for async prediction results.

**Auth:** `viewer`+

**Response `200`:**

```json
{
  "task_id": "abc123def456",
  "status": "completed",
  "mask_path": "/results/abc123/mask.png",
  "overlay_path": "/results/abc123/overlay.png",
  "area_km2": 1.234,
  "model_name": "unet",
  "image_path": "/results/abc123/input.tif"
}
```

---

## Model Comparison

### `POST /api/compare`

Run the same image through multiple models side-by-side.

**Auth:** `analyst`+ | **Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | yes | GeoTIFF satellite image |
| `model_names` | string | yes | Comma-separated model names |
| `use_tta` | boolean | no | Test-time augmentation |
| `use_crf` | boolean | no | CRF post-processing |

**Response `200`:**

```json
{
  "task_id": "compare-abc123",
  "segments": [
    {
      "model_name": "unet",
      "mask_path": "/results/compare-abc123/unet_mask.png",
      "overlay_path": "/results/compare-abc123/unet_overlay.png",
      "area_km2": 1.234
    },
    {
      "model_name": "random_forest",
      "mask_path": "/results/compare-abc123/rf_mask.png",
      "overlay_path": "/results/compare-abc123/rf_overlay.png",
      "area_km2": 1.189
    }
  ]
}
```

---

## Temporal Trend

### `POST /api/trend`

Compute glacier area change over time with linear regression and optional forecast.

**Auth:** `analyst`+ | **Content-Type:** `application/json`

```json
{
  "file_ids": ["id1", "id2", "id3"],
  "years": [2000, 2005, 2010],
  "forecast_until": 2050
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_ids` | string[] | yes | History record IDs to analyze |
| `years` | number[] | yes | Corresponding years for each ID |
| `forecast_until` | number | no | Forecast horizon. Default `2050` |

**Response `200`:**

```json
{
  "data": [
    {"year": 2000, "area_km2": 2.5},
    {"year": 2005, "area_km2": 2.3},
    {"year": 2010, "area_km2": 2.0}
  ],
  "forecast": [
    {"year": 2015, "area_km2": 1.8, "ci_lower": 1.6, "ci_upper": 2.0},
    {"year": 2050, "area_km2": 0.5, "ci_lower": 0.1, "ci_upper": 0.9}
  ],
  "loss_rate_km2_per_year": -0.1,
  "total_loss_percent": 20.0,
  "r_squared": 0.95,
  "p_value": 0.01,
  "significant": true
}
```

---

## Export

### `GET /api/export/{task_id}`

Download segmentation results in various formats.

**Auth:** `viewer`+ | **Query param:** `fmt` (optional, default `json`)

| Format | Description |
|--------|-------------|
| `json` | Full result metadata as JSON |
| `geojson` | Glacier mask as GeoJSON polygon |
| `csv` | Area statistics as CSV |

---

## History

### `GET /api/history`

List past prediction results.

**Auth:** `viewer`+

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Skip first N |

**Response `200`:** Array of history items:

```json
[
  {
    "id": 1,
    "task_id": "abc123def456",
    "model_name": "unet",
    "area_km2": 1.234,
    "year": 2020,
    "created_at": "2025-01-15T10:30:00",
    "thumbnail_path": "/results/abc123/thumb.png",
    "mask_path": "/results/abc123/mask.png",
    "overlay_path": "/results/abc123/overlay.png",
    "image_path": "/results/abc123/input.tif",
    "status": "completed"
  }
]
```

### `DELETE /api/history/{task_id}`

Delete a history record and its associated files.

**Auth:** `admin`**

**Response `200`:**

```json
{"detail": "Deleted task abc123def456"}
```

---

## Task Management

### `POST /api/tasks/create`

Create a new background task.

**Auth:** `analyst`+

```json
{
  "name": "Train U-Net model",
  "description": "Retrain on updated dataset",
  "priority": 5,
  "metadata": {"dataset": "v2", "epochs": 100}
}
```

**Response `201`:**

```json
{
  "id": "task-a1b2c3d4e5f6",
  "name": "Train U-Net model",
  "status": "pending",
  "progress": 0.0,
  "result": null,
  "error": null
}
```

### `GET /api/tasks/{task_id}`

Get task status and progress.

**Response `200`:** `TaskResponse` (see above)

### `POST /api/tasks/{task_id}/cancel`

Cancel a pending or running task. Returns `409` if the task is already in a terminal state (`completed`, `failed`, `cancelled`).

**Response `200`:** `TaskResponse` with `status: "cancelled"`

### `GET /api/tasks/active`

List all non-terminal tasks (pending or running).

**Response `200`:** Array of `TaskResponse`

### `GET /api/tasks/`

List all tasks with pagination.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `offset` | int | 0 | Skip first N |
| `limit` | int | 20 | Max results (1–100) |

**Response `200`:**

```json
{
  "tasks": [...],
  "total": 42,
  "offset": 0,
  "limit": 20
}
```

---

## Dataset Management

### `GET /api/datasets/`

List all registered datasets.

### `POST /api/datasets/create`

Register a new dataset.

```json
{
  "name": "Sentinel-2 2020",
  "year": 2020,
  "source": "sentinel2",
  "description": "High-resolution summer composite"
}
```

### `GET /api/datasets/{id}`

Get dataset metadata.

### `DELETE /api/datasets/{id}`

Delete a dataset and its associated files.

### `POST /api/datasets/{id}/upload`

Upload files to a dataset. **Content-Type:** `multipart/form-data`

### `GET /api/datasets/{id}/validate`

Validate dataset integrity (file checksums, format checks).

### `GET /api/datasets/{id}/samples`

Get sample images from the dataset.

### `GET /api/datasets/{id}/stats`

Get dataset statistics (band ranges, file counts, coverage).

---

## Training

### `POST /api/training/start`

Start a training run.

```json
{
  "model_type": "unet",
  "dataset_id": "ds-abc123",
  "epochs": 100,
  "batch_size": 8,
  "learning_rate": 0.0001,
  "use_attention": false
}
```

### `GET /api/training/status`

Get current training status.

### `POST /api/training/stop`

Stop the active training run.

### `POST /api/training/resume`

Resume a paused training run.

### `GET /api/training/history`

List past training runs.

### `GET /api/training/models`

List saved model artifacts.

### `DELETE /api/training/models/{model_id}`

Delete a model artifact.

### `GET /api/training/config`

Get available training configurations.

---

## Monitoring

### `GET /api/monitoring/metrics`

Prometheus text-format metrics endpoint.

**Response `200`** (`Content-Type: text/plain; version=0.0.4`):

```
# HELP glacierkz_uptime_seconds Process uptime in seconds.
# TYPE glacierkz_uptime_seconds gauge
glacierkz_uptime_seconds 3600.00

# HELP glacierkz_cpu_percent Current CPU usage percentage.
# TYPE glacierkz_cpu_percent gauge
glacierkz_cpu_percent 12.50

# HELP glacierkz_memory_rss_bytes Resident set size in bytes.
# TYPE glacierkz_memory_rss_bytes gauge
glacierkz_memory_rss_bytes 524288000

# HELP glacierkz_open_fds Number of open file descriptors.
# TYPE glacierkz_open_fds gauge
glacierkz_open_fds 42

# HELP glacierkz_threads Number of threads in the process.
# TYPE glacierkz_threads gauge
glacierkz_threads 8
```

### `GET /api/monitoring/system`

Detailed system resource metrics (JSON).

```json
{
  "uptime_seconds": 3600.00,
  "cpu": {
    "percent": 12.5,
    "count_logical": 8,
    "count_physical": 4,
    "load_avg_1m": 0.5,
    "load_avg_5m": 0.3,
    "load_avg_15m": 0.2
  },
  "memory": {
    "total_bytes": 8589934592,
    "available_bytes": 4294967296,
    "used_bytes": 4294967296,
    "percent": 50.0,
    "total_human": "8.0 GB",
    "used_human": "4.0 GB"
  },
  "disk": {
    "total_bytes": 107374182400,
    "used_bytes": 53687091200,
    "free_bytes": 53687091200,
    "percent": 50.0,
    "total_human": "100.0 GB",
    "used_human": "50.0 GB"
  },
  "process": {
    "pid": 12345,
    "rss_bytes": 524288000,
    "threads": 8,
    "open_fds": 42
  }
}
```

### `GET /api/monitoring/status`

Lightweight health summary for liveness probes.

```json
{
  "status": "healthy",
  "uptime_seconds": 3600.00,
  "cpu_percent": 12.5,
  "memory_percent": 50.0,
  "checks": {
    "cpu_ok": true,
    "memory_ok": true
  }
}
```

Status is `healthy` when CPU < 95% and memory < 95%; otherwise `degraded`.

---

## LLM Analysis

### `GET /api/analysis/models`

List available LLM providers and models.

**Response `200`:**

```json
[
  {
    "provider": "openai",
    "label": "OpenAI",
    "models": [
      {"id": "gpt-4o", "name": "GPT-4o", "free": false}
    ],
    "needs_key": true
  },
  {
    "provider": "ollama",
    "label": "Ollama (local)",
    "models": [
      {"id": "llama3", "name": "Llama 3", "free": true}
    ],
    "needs_key": false
  }
]
```

### `POST /api/analysis/analyze`

Send analysis prompt to an LLM provider.

```json
{
  "prompt": "Describe the glacier retreat pattern in the Almaty region",
  "provider": "ollama",
  "model": "llama3",
  "mode": "describe",
  "context": "Time series data: 2000=2.5km², 2010=2.0km², 2020=1.5km²",
  "api_key": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | yes | Analysis question |
| `provider` | string | no | LLM provider (auto-selects if omitted) |
| `model` | string | no | Model ID |
| `mode` | string | no | `describe`, `trend`, or `compare` |
| `context` | string | no | Additional context for the LLM |
| `api_key` | string | no | Provider API key (overrides env) |

**Response `200`:**

```json
{
  "content": "The glacier shows a consistent retreat pattern...",
  "provider": "ollama",
  "model": "llama3",
  "fallback_used": false
}
```

---

## WebSocket

**Endpoint:** `ws://localhost:8000/ws/{client_id}`

The WebSocket provides real-time task progress, results, and pub/sub messaging.

### Connection

On connect, the server sends:

```json
{"type": "connected", "client_id": "your-client-id"}
```

### Client Messages

| Type | Payload | Description |
|------|---------|-------------|
| `ping` | `{}` | Heartbeat (server responds with `pong`) |
| `join_room` | `{"room": "training-run-123"}` | Subscribe to a room |
| `leave_room` | `{"room": "training-run-123"}` | Unsubscribe from a room |
| `broadcast` | `{"room": "room-name", "message": {...}}` | Broadcast to room |

### Server Messages

| Type | Description |
|------|-------------|
| `connected` | Connection confirmation |
| `pong` | Heartbeat response |
| `room_joined` | Confirmed room subscription |
| `progress` | Task progress update |
| `result` | Task completion with result payload |
| `error` | Task failure |
| `notification` | Info/warning/error notification |

**Progress message:**

```json
{
  "type": "progress",
  "task_id": "task-abc123",
  "progress": 65.0,
  "message": "Processing band 4",
  "stage": "inference",
  "timestamp": 1700000000.0
}
```

**Result message:**

```json
{
  "type": "result",
  "task_id": "task-abc123",
  "result": {
    "area_km2": 1.234,
    "mask_path": "/results/task-abc123/mask.png"
  },
  "timestamp": 1700000010.0
}
```

### Heartbeat

The server pings all clients every 30 seconds. Clients that haven't responded in 60 seconds are disconnected.

---

## MCP Tools

The Model Context Protocol server exposes 10 tools for LLM clients.
See [`glacierkz-mcp/README.md`](../glacierkz-mcp/README.md) for connection setup.

| Tool | Description |
|------|-------------|
| `list_data_years` | All available Landsat/Sentinel-2 years |
| `list_predictions` | Pre-computed glacier areas per year/model |
| `get_image_metadata(year)` | CRS, resolution, band count, file size |
| `get_band_statistics(year)` | Per-band mean/std/min/max (excludes NaN) |
| `query_pixel(year, longitude, latitude)` | Spectral signature at a point |
| `get_glacier_area(year, model)` | Area stats for one year + model |
| `get_all_glacier_areas` | Comparison table across all years |
| `get_glacier_time_series` | Change-over-time table |
| `get_study_area_info` | Region, glaciers, bounding box |
| `get_available_models` | Model status, type, years predicted |

### Tool Details

#### `list_data_years`

Returns all years with available satellite data.

```json
{
  "landsat_years": [2000, 2003, 2006, 2009, 2011, 2013],
  "sentinel2_years": [2016, 2017, 2020],
  "total_years": 9
}
```

#### `get_glacier_time_series`

Returns glacier area change over time.

```json
[
  {"year": 2000, "model": "ensemble", "area_km2": 2.5, "source": "landsat"},
  {"year": 2010, "model": "ensemble", "area_km2": 2.1, "source": "landsat"},
  {"year": 2020, "model": "ensemble", "area_km2": 1.6, "source": "sentinel2"}
]
```

#### `query_pixel(year, longitude, latitude)` 

Returns spectral values at a geographic coordinate.

```json
{
  "year": 2020,
  "longitude": 77.06,
  "latitude": 43.05,
  "bands": {
    "B2": 8500, "B3": 9200, "B4": 7800, "B8": 8100,
    "B8A": 7900, "B11": 2100, "B12": 1800,
    "NDSI": 0.65, "NDWI": 0.32, "BSI": -0.15, "EVI": 0.48
  }
}
```
