#!/usr/bin/env bash
# Restore Leaflet PNG assets (npm may omit them when install scripts are blocked).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT"
if [[ -d "$ROOT/glacierkz-web/node_modules" ]]; then
  WEB="$ROOT/glacierkz-web"
fi
DEST="$WEB/node_modules/leaflet/dist/images"
PUBLIC="$WEB/public/leaflet"
mkdir -p "$DEST" "$PUBLIC"
BASE="https://unpkg.com/leaflet@1.9.4/dist/images"
for f in marker-icon.png marker-icon-2x.png marker-shadow.png layers.png layers-2x.png; do
  curl -sfL "$BASE/$f" -o "$PUBLIC/$f"
  cp "$PUBLIC/$f" "$DEST/$f"
done
echo "Leaflet assets installed to $PUBLIC and $DEST"
