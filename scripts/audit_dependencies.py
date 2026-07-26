#!/usr/bin/env python3
"""Run pip-audit with a bounded, machine-enforced exception registry."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "security-exceptions.json"


def load_active_exception_ids(today: date | None = None) -> list[str]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if payload.get("schema") != "glaciernet-kz.security-exceptions.v1":
        raise ValueError("Invalid security exception registry schema")
    review_by = date.fromisoformat(payload["review_by"])
    current = today or date.today()
    if current > review_by:
        raise RuntimeError(f"Security exceptions expired on {review_by}; review dependencies before continuing")
    exceptions = payload.get("exceptions")
    if not isinstance(exceptions, list) or not exceptions:
        raise ValueError("Security exception registry is empty or invalid")
    ids = [item["id"] for item in exceptions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate security exception IDs")
    return ids


def main() -> int:
    command = [
        sys.executable,
        "-m",
        "pip_audit",
        "-r",
        str(ROOT / "requirements.txt"),
        "-r",
        str(ROOT / "glacierkz-api/requirements-api.txt"),
    ]
    for vulnerability_id in load_active_exception_ids():
        command.extend(["--ignore-vuln", vulnerability_id])
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
