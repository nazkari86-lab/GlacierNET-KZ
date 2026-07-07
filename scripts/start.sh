#!/usr/bin/env bash
# GlacierNET-KZ — start entire stack on one URL: http://localhost:8080
#
# Usage:
#   ./scripts/start.sh          # Docker (recommended)
#   ./scripts/start.sh --native # Local processes + Caddy in Docker
#   ./scripts/start.sh --stop     # Stop native processes

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PID_DIR="$ROOT/.run"
LOG_DIR="$ROOT/logs/unified"
GATEWAY_PORT="${GATEWAY_PORT:-8080}"
API_PORT=8000
WEB_PORT=3000
DEMO_PORT=7860

mkdir -p "$PID_DIR" "$LOG_DIR"

stop_native() {
  echo "Stopping GlacierNET-KZ services..."
  for f in api web demo; do
    if [[ -f "$PID_DIR/$f.pid" ]]; then
      kill "$(cat "$PID_DIR/$f.pid")" 2>/dev/null || true
      rm -f "$PID_DIR/$f.pid"
    fi
  done
  if [[ -f "$PID_DIR/gateway.cid" ]]; then
    docker rm -f "$(cat "$PID_DIR/gateway.cid")" 2>/dev/null || true
    rm -f "$PID_DIR/gateway.cid"
  fi
  docker rm -f glacierkz-gateway 2>/dev/null || true
  echo "Done."
}

if [[ "${1:-}" == "--stop" ]]; then
  stop_native
  exit 0
fi

if [[ "${1:-}" != "--native" ]]; then
  echo "🏔️  GlacierNET-KZ — Docker unified stack"
  echo "    → http://localhost:${GATEWAY_PORT}"
  echo ""
  docker compose up --build
  exit 0
fi

# ── Native mode (faster for development) ──────────────────────────
stop_native

pick_python() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    echo "$ROOT/.venv/bin/python"
  else
    command -v python3
  fi
}

PYTHON="$(pick_python)"

if ! "$PYTHON" -c "import uvicorn" 2>/dev/null; then
  echo "Install dependencies first: pip install -r requirements.txt -r glacierkz-api/requirements-api.txt"
  exit 1
fi

export PYTHONPATH="$ROOT"
export CORE_DIR="$ROOT"
export DATA_DIR="$ROOT/glacierkz-api/data"

echo "🏔️  GlacierNET-KZ — native unified stack"
echo "    Gateway → http://localhost:${GATEWAY_PORT}"
echo "    Logs    → $LOG_DIR/"
echo ""

# API
(
  cd "$ROOT/glacierkz-api"
  "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" \
    >"$LOG_DIR/api.log" 2>&1 &
  echo $! >"$PID_DIR/api.pid"
)

# Gradio demo
(
  cd "$ROOT/spaces"
  GRADIO_ROOT_PATH=/demo DEMO_PORT="$DEMO_PORT" \
    "$PYTHON" app.py >"$LOG_DIR/demo.log" 2>&1 &
  echo $! >"$PID_DIR/demo.pid"
)

# Next.js
if [[ -d "$ROOT/glacierkz-web/node_modules" ]]; then
  (
    cd "$ROOT/glacierkz-web"
    API_INTERNAL_URL="http://127.0.0.1:${API_PORT}" \
    NEXT_PUBLIC_API_URL="" \
    NEXT_PUBLIC_SITE_URL="http://localhost:${GATEWAY_PORT}" \
      npm run dev -- --port "$WEB_PORT" >"$LOG_DIR/web.log" 2>&1 &
    echo $! >"$PID_DIR/web.pid"
  )
else
  echo "⚠️  glacierkz-web/node_modules missing — run: cd glacierkz-web && npm ci"
fi

# Wait for backends
for i in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1 && break
  sleep 1
done

# Caddy gateway (Docker, routes to host)
docker rm -f glacierkz-gateway 2>/dev/null || true
GATEWAY_CID=$(docker run -d --name glacierkz-gateway \
  -p "${GATEWAY_PORT}:8080" \
  -v "$ROOT/gateway/Caddyfile.native:/etc/caddy/Caddyfile:ro" \
  --add-host=host.docker.internal:host-gateway \
  caddy:2-alpine 2>"$LOG_DIR/gateway.log")
echo "$GATEWAY_CID" >"$PID_DIR/gateway.cid"

cat <<EOF

✅ All services started

  Dashboard    http://localhost:${GATEWAY_PORT}/
  Gradio demo  http://localhost:${GATEWAY_PORT}/demo
  API docs     http://localhost:${GATEWAY_PORT}/docs
  MCP tools    http://localhost:${GATEWAY_PORT}/mcp/tools
  Classic UI   http://localhost:${GATEWAY_PORT}/legacy
  Health       http://localhost:${GATEWAY_PORT}/health

  Stop: ./scripts/start.sh --stop

EOF

# Keep script alive while services run (Ctrl+C to stop)
trap 'stop_native; exit 0' INT TERM
while true; do sleep 3600; done
