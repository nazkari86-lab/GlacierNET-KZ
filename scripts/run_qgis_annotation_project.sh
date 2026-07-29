#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QGIS_APP="/Applications/QGIS-final-4_0_2.app"
QGIS_BIN="$QGIS_APP/Contents/MacOS/QGIS-final-4_0_2"
PROFILE_DIR="${TMPDIR:-/tmp}/glaciernet-kz-qgis-profile"

if [[ ! -x "$QGIS_BIN" ]]; then
  echo "QGIS executable not found: $QGIS_BIN" >&2
  exit 1
fi

export GLACIERNET_ROOT="$ROOT"
export QGIS_CUSTOM_CONFIG_PATH="$PROFILE_DIR"
export QGIS_PREFIX_PATH="$QGIS_APP"
export QGIS_PLUGINPATH="$QGIS_APP/Contents/Resources/qgis/python/plugins"
export PYTHONPATH="$QGIS_APP/Contents/Resources/python3.11/site-packages:$QGIS_APP/Contents/Resources/qgis/python"
export PROJ_DATA="$QGIS_APP/Contents/Resources/qgis/proj"
export GDAL_DATA="$QGIS_APP/Contents/Resources/qgis/gdal"

exec "$QGIS_BIN" \
  --nologo \
  --noversioncheck \
  --code "$ROOT/scripts/create_qgis_annotation_project.py"
