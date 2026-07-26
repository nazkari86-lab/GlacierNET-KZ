# Unified Local Stack

> All GlacierNET-KZ services behind one URL: **http://localhost:8080**

## Architecture

```
                    http://localhost:8080
                            │
                     ┌──────▼──────┐
                     │   Caddy     │
                     │  (gateway)  │
                     └──────┬──────┘
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐     ┌──────▼──────┐   ┌──────▼──────┐
    │  Next.js  │     │   FastAPI   │   │   Gradio    │
    │  web:3000 │     │  api:8000   │   │ demo:7860   │
    └───────────┘     └──────┬──────┘   └─────────────┘
                             │
                      ┌──────▼──────┐
                      │    Redis    │
                      └─────────────┘
```

## Routes

| Path | Service | Description |
|------|---------|-------------|
| `/` | Next.js | Home page |
| `/hub` | Next.js | Service directory (start here) |
| `/dashboard` | Next.js | Monitoring dashboard |
| `/explore` | Next.js | Browse and compare locally available years without uploads |
| `/glaciers` | Next.js | Search individual RGI glaciers and inspect mask time series |
| `/predict` | Next.js | Segmentation UI |
| `/demo` | Gradio | Quick upload demo |
| `/docs` | FastAPI | OpenAPI Swagger |
| `/api/*` | FastAPI | REST endpoints |
| `/api/years` | FastAPI | Verified local year metadata and physical artifacts |
| `/api/glaciers` | FastAPI | RGI registry, individual time series, and evidence-card export |
| `/mcp/*` | FastAPI | MCP tools bridge |
| `/legacy` | FastAPI | Classic static UI |
| `/health` | FastAPI | Health check |
| `/ws` | FastAPI | WebSocket events |

## Start

```bash
# Docker (recommended)
./scripts/start.sh

# Native dev (hot reload)
./scripts/start.sh --native

# Stop native processes
./scripts/start.sh --stop
```

## Environment

When using the unified gateway, set empty API URL so the browser uses same-origin requests:

```
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_SITE_URL=http://localhost:8080
```

The Docker stack mounts `data/raw/`, `data/processed/`, `predictions/`,
`results/`, and `models/` read-only into the API/demo containers. Generated
uploads and API results remain in dedicated Docker volumes.

## Easiest verification flow

1. Open `http://localhost:8080/explore`.
2. Select any locally indexed year. No image upload is required.
3. Inspect the decision-ready area, quality score, sensor, caveat, physical
   method artifacts, overlay, and provenance availability.
4. Select a second year and run the comparison. The API marks comparisons
   involving an excluded year as not strictly comparable.
5. Use `/predict` only for a new 7+ band scientific GeoTIFF. Ordinary PNG,
   JPEG, screenshots, and phone photos are not valid model inputs.

## Individual glacier evidence

`/glaciers` is the default path when the user knows which glacier they need.
The API reads the physical `rgi_study_area.shp` subset and intersects each
selected glacier with on-disk prediction masks. It does not fabricate annual
outlines. The resulting series is constrained to the fixed RGI 2000 polygon,
which makes it useful for consistent screening and expert review but not a
replacement for independent annual delineation or field validation.

Tuyuksu includes locally downloaded WGMS reference points. Water-equivalent,
ice-volume, runoff, and downstream-impact claims remain disabled until an
explicitly validated thickness/hydrology dataset is connected.

## Standalone MCP server

For Claude Code / Cursor (stdio), the separate MCP server still works:

```bash
cd glacierkz-mcp && python server.py
```

The API MCP bridge at `/mcp/tools` exposes a subset for HTTP clients.
