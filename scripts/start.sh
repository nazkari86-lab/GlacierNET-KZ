#!/usr/bin/env bash
# GlacierNET-KZ — start entire stack on one URL: http://localhost:8080
#
# Usage:
#   ./scripts/start.sh          # Docker (recommended)
#   ./scripts/start.sh --native # Local processes; Caddy gateway when Docker is available
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
ENABLE_LEGACY_DEMO="${ENABLE_LEGACY_DEMO:-0}"

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
  if [[ -x "$ROOT/.venv/bin/python" ]] && "$ROOT/.venv/bin/python" -c "import uvicorn" 2>/dev/null; then
    echo "$ROOT/.venv/bin/python"
  elif [[ -x "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python" ]]; then
    echo "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python"
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

# The Gradio app duplicates the primary Next.js workflow and costs memory.
# Keep it available for explicit compatibility checks, but do not start it as
# part of the default product stack.
if [[ "$ENABLE_LEGACY_DEMO" == "1" ]]; then
  (
    cd "$ROOT/spaces"
    GRADIO_ROOT_PATH=/demo DEMO_PORT="$DEMO_PORT" \
      "$PYTHON" app.py >"$LOG_DIR/demo.log" 2>&1 &
    echo $! >"$PID_DIR/demo.pid"
  )
fi

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
  echo "glacierkz-web/node_modules is missing — run: cd glacierkz-web && npm ci"
  stop_native
  exit 1
fi

wait_for_service() {
  local name="$1"
  local url="$2"
  local pid_file="$3"
  local log_file="$4"
  local attempts="${5:-40}"
  for _ in $(seq 1 "$attempts"); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "    ✓ $name ready"
      return 0
    fi
    if [[ ! -f "$pid_file" ]] || ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "$name stopped before becoming ready."
      tail -n 30 "$log_file" 2>/dev/null || true
      return 1
    fi
    sleep 1
  done
  echo "$name did not become ready at $url."
  tail -n 30 "$log_file" 2>/dev/null || true
  return 1
}

if ! wait_for_service "API" "http://127.0.0.1:${API_PORT}/health" "$PID_DIR/api.pid" "$LOG_DIR/api.log"; then
  stop_native
  exit 1
fi
if ! wait_for_service "Web" "http://127.0.0.1:${WEB_PORT}/" "$PID_DIR/web.pid" "$LOG_DIR/web.log"; then
  stop_native
  exit 1
fi
if [[ "$ENABLE_LEGACY_DEMO" == "1" ]] && \
  ! wait_for_service "Legacy demo" "http://127.0.0.1:${DEMO_PORT}/" "$PID_DIR/demo.pid" "$LOG_DIR/demo.log"; then
  stop_native
  exit 1
fi

PUBLIC_URL="http://localhost:${WEB_PORT}"
GATEWAY_NOTE="Docker is unavailable; use the Next.js URL directly."

# Caddy is convenient but optional in native development.  Do not leave the
# API and web processes stranded merely because Docker Desktop is closed.
if docker info >/dev/null 2>&1; then
  docker rm -f glacierkz-gateway 2>/dev/null || true
  GATEWAY_CID=$(docker run -d --name glacierkz-gateway \
    -p "${GATEWAY_PORT}:8080" \
    -v "$ROOT/gateway/Caddyfile.native:/etc/caddy/Caddyfile:ro" \
    --add-host=host.docker.internal:host-gateway \
    caddy:2-alpine 2>"$LOG_DIR/gateway.log")
  echo "$GATEWAY_CID" >"$PID_DIR/gateway.cid"
  PUBLIC_URL="http://localhost:${GATEWAY_PORT}"
  GATEWAY_NOTE="Caddy gateway is running."
else
  echo "⚠️  Docker Desktop is not running; continuing without the optional Caddy gateway."
fi

cat <<EOF

✅ All services started

  Dashboard    ${PUBLIC_URL}/
  API docs     http://127.0.0.1:${API_PORT}/docs
  Health       http://127.0.0.1:${API_PORT}/health
  ${GATEWAY_NOTE}
  Legacy demo  ${ENABLE_LEGACY_DEMO} (set ENABLE_LEGACY_DEMO=1 to enable)

  Stop: ./scripts/start.sh --stop

EOF

# Keep the launcher attached and fail visibly if a required service exits.
trap 'stop_native; exit 0' INT TERM
while true; do
  sleep 5
  for service in api web; do
    if [[ ! -f "$PID_DIR/$service.pid" ]] || ! kill -0 "$(cat "$PID_DIR/$service.pid")" 2>/dev/null; then
      echo "Required service '$service' stopped. See $LOG_DIR/$service.log"
      stop_native
      exit 1
    fi
  done
  if [[ "$ENABLE_LEGACY_DEMO" == "1" ]] && \
    { [[ ! -f "$PID_DIR/demo.pid" ]] || ! kill -0 "$(cat "$PID_DIR/demo.pid")" 2>/dev/null; }; then
    echo "Legacy demo stopped. See $LOG_DIR/demo.log"
    stop_native
    exit 1
  fi
done
