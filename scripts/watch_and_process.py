#!/usr/bin/env python3
"""Watch for downloaded GeoTIFFs and run inference + post-processing."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config

LOG = ROOT / "logs" / "watch_process.log"
DRIVE_LIST = json.loads((ROOT / "drive_file_list.json").read_text())
EXPECTED = [e["name"] for e in DRIVE_LIST if "subset" not in e["name"]]


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def find_tif(name: str) -> Path | None:
    if name.startswith("sentinel2"):
        p = config.DATA_RAW_SENTINEL2 / name
    else:
        p = config.DATA_RAW_LANDSAT / name
    return p if p.exists() and p.stat().st_size > 1_000_000 else None


def year_from_name(name: str) -> int:
    import re
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else 0


def run_predict(year: int) -> None:
  log(f"Running predict.py --year {year} --save")
  subprocess.run(
      [sys.executable, str(ROOT / "predict.py"), "--year", str(year), "--save"],
      cwd=str(ROOT),
      check=False,
  )


def main() -> None:
    log("Watching for GeoTIFF downloads...")
    processed: set[str] = set()

    while True:
        ready = []
        for name in EXPECTED:
            if name in processed:
                continue
            if find_tif(name):
                ready.append(name)

        for name in ready:
            year = year_from_name(name)
            if year:
                run_predict(year)
            processed.add(name)
            log(f"Processed {name} ({len(processed)}/{len(EXPECTED)})")

        if len(processed) >= len(EXPECTED):
            log("All GeoTIFFs processed. Running generate_figures + seed_db...")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_figures.py")], cwd=str(ROOT))
            subprocess.run([sys.executable, str(ROOT / "glacierkz-api" / "seed_db.py")], cwd=str(ROOT))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "pipeline_status.py")], cwd=str(ROOT))
            log("Post-download pipeline complete.")
            break

        time.sleep(120)


if __name__ == "__main__":
    main()
