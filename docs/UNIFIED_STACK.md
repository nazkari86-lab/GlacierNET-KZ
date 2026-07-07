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
| `/predict` | Next.js | Segmentation UI |
| `/demo` | Gradio | Quick upload demo |
| `/docs` | FastAPI | OpenAPI Swagger |
| `/api/*` | FastAPI | REST endpoints |
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

## Standalone MCP server

For Claude Code / Cursor (stdio), the separate MCP server still works:

```bash
cd glacierkz-mcp && python server.py
```

The API MCP bridge at `/mcp/tools` exposes a subset for HTTP clients.
