#!/usr/bin/env python3
"""Create a deterministic manifest for every project data artifact.

The manifest deliberately records symlinks as unresolved.  A release must
contain regular files; this makes Google Drive-backed development copies fail
closed instead of silently looking reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(ROOT).as_posix()
        record: dict[str, object] = {
            "path": relative,
            "kind": "symlink" if path.is_symlink() else "file",
            "size_bytes": path.stat().st_size if path.exists() else None,
        }
        if path.is_symlink():
            record["target"] = os.readlink(path)
            record["status"] = "unresolved" if not path.exists() else "external-or-linked"
            if path.is_file():
                record["sha256"] = sha256(path)
        elif path.is_file():
            record["sha256"] = sha256(path)
            record["status"] = "verified"
        records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "data_manifest.json")
    parser.add_argument("--root", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    root = args.root.resolve()
    records = collect(root)
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project_root": str(ROOT),
        "data_root": str(root),
        "file_count": sum(r["kind"] == "file" for r in records),
        "symlink_count": sum(r["kind"] == "symlink" for r in records),
        "unresolved_count": sum(r.get("status") == "unresolved" for r in records),
        "artifacts": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {args.output}")
    print(
        f"Files: {payload['file_count']}; symlinks: {payload['symlink_count']}; unresolved: {payload['unresolved_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
