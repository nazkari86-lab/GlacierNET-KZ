#!/usr/bin/env python3
"""Validate saved CryoGenesis passports and bundle checksums."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cryogenesis.passport import verify_passport
from src.cryogenesis.source_registry import sha256_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path("results/cryogenesis/current"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    errors: list[str] = []
    passports = sorted((root / "passports").glob("*.json"))
    if not passports:
        errors.append("no passports found")
    for path in passports:
        result = verify_passport(json.loads(path.read_text(encoding="utf-8")))
        if not result.valid:
            errors.append(f"{path.name}: {', '.join(result.errors)}")
    checksums = root / "checksums.sha256"
    if not checksums.is_file():
        errors.append("checksums.sha256 missing")
    else:
        for line in checksums.read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                errors.append(f"missing checksum target: {relative}")
            elif sha256_file(path) != digest:
                errors.append(f"checksum mismatch: {relative}")
    print(
        json.dumps(
            {
                "valid": not errors,
                "passport_count": len(passports),
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
