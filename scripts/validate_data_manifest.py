#!/usr/bin/env python3
"""Fail-closed validation for a release data manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_link(path: Path, item: dict[str, object], errors: list[str]) -> None:
    """Validate an external link without pretending it is an embedded file."""
    if not path.exists():
        errors.append(f"broken symlink: {item['path']}")
        return
    if item.get("target") is None:
        errors.append(f"symlink has no recorded target: {item['path']}")
        return
    if path.is_file() and item.get("size_bytes") is not None and path.stat().st_size != item["size_bytes"]:
        errors.append(f"linked size mismatch: {item['path']}")
    if path.is_file() and item.get("sha256") and digest(path) != item["sha256"]:
        errors.append(f"linked sha256 mismatch: {item['path']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path, default=ROOT / "results" / "data_manifest.json")
    parser.add_argument("--allow-symlinks", action="store_true", help="allow verified external links")
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    for item in payload.get("artifacts", []):
        path = ROOT / item["path"]
        if item["kind"] == "symlink":
            if not args.allow_symlinks:
                errors.append(f"symlink is not release-safe: {item['path']}")
            else:
                validate_link(path, item, errors)
            continue
        if not path.is_file():
            errors.append(f"missing file: {item['path']}")
            continue
        if path.stat().st_size != item["size_bytes"]:
            errors.append(f"size mismatch: {item['path']}")
            continue
        if digest(path) != item["sha256"]:
            errors.append(f"sha256 mismatch: {item['path']}")
    if errors:
        print("DATA MANIFEST VALIDATION FAILED")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Data manifest validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
