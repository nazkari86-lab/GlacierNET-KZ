#!/bin/zsh
# Persistent supervisor: restart the Drive downloader after any process-level
# failure. It exits only after every requested TIFF is verified complete.
set -u

root="${GLACIERNET_KZ_ROOT:?Set GLACIERNET_KZ_ROOT first}"
repo="${GLACIERNET_REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
python_bin="${GLACIERNET_PYTHON:-/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python}"
workers="${GLACIERNET_WORKERS:-4}"
log_file="${GLACIERNET_DOWNLOAD_LOG:-$repo/download_forever.log}"

mkdir -p "$root/data/raw/sentinel2" "$root/data/raw/landsat"
attempt=0
while true; do
  attempt=$((attempt + 1))
  print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] supervisor attempt=$attempt workers=$workers" >> "$log_file"
  GLACIERNET_KZ_ROOT="$root" "$python_bin" "$repo/download_drive.py" \
    --workers "$workers" --retries 20 --retry-delay 20 >> "$log_file" 2>&1
  status=$?
  if [[ "$status" -eq 0 ]]; then
    print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] completed" >> "$log_file"
    exit 0
  fi
  print -r -- "[$(date '+%Y-%m-%d %H:%M:%S')] process exited status=$status; restart in 30s" >> "$log_file"
  sleep 30
done
