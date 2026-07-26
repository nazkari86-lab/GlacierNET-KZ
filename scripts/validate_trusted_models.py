#!/usr/bin/env python3
"""Verify every artifact in the model trust registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model_security import TRUST_SCHEMA, verify_trusted_model  # noqa: E402


def main() -> int:
    registry_path = ROOT / "models/trusted_artifacts.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if payload.get("schema") != TRUST_SCHEMA or not isinstance(payload.get("artifacts"), dict):
        raise ValueError(f"Invalid model trust registry: {registry_path}")
    for relative in sorted(payload["artifacts"]):
        verify_trusted_model(ROOT / relative, root=ROOT)
        print(f"verified: {relative}")
    print(f"Trusted model validation passed ({len(payload['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
