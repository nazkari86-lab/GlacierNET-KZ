#!/usr/bin/env python3
"""Restart the Drive downloader until every TIFF is verified complete."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = Path(os.getenv("GLACIERNET_DOWNLOAD_LOG", ROOT / "download_forever.log"))


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")


def main() -> int:
    python = os.getenv("GLACIERNET_PYTHON", sys.executable)
    workers = os.getenv("GLACIERNET_WORKERS", "4")
    root = os.getenv("GLACIERNET_KZ_ROOT")
    if not root:
        raise SystemExit("GLACIERNET_KZ_ROOT is required")
    while True:
        log(f"supervisor starting downloader workers={workers}")
        result = subprocess.run(
            [python, str(ROOT / "download_drive.py"), "--workers", workers, "--retries", "20", "--retry-delay", "20"],
            cwd=ROOT,
            env={**os.environ, "GLACIERNET_KZ_ROOT": root},
        )
        if result.returncode == 0:
            log("all downloads completed")
            return 0
        log(f"downloader exited {result.returncode}; restart in 30 seconds")
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
