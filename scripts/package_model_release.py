#!/usr/bin/env python3
"""Build deterministic, checksum-verified model archives for a GitHub release."""

from __future__ import annotations

import argparse
import gzip
import json
import tarfile
from pathlib import Path

from src.provenance import sha256_directory, sha256_file

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "releases/model_artifacts.v1.json"


def _normalized_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = 0o755 if info.isdir() else 0o644
    info.pax_headers = {}
    return info


def build_deterministic_archive(source: Path, destination: Path) -> None:
    """Archive one directory with stable ordering and normalized metadata."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                entries = [source, *sorted(source.rglob("*"))]
                for entry in entries:
                    if entry.is_symlink():
                        raise ValueError(f"Release model must not contain symlinks: {entry}")
                    arcname = source.name if entry == source else f"{source.name}/{entry.relative_to(source)}"
                    archive.add(
                        entry,
                        arcname=arcname,
                        recursive=False,
                        filter=_normalized_tarinfo,
                    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    packaged: list[dict[str, object]] = []
    for artifact in manifest["artifacts"]:
        source = ROOT / artifact["local_path"]
        if not source.is_dir():
            raise FileNotFoundError(f"Missing model directory: {source}")
        actual_directory_hash = sha256_directory(source)
        if actual_directory_hash != artifact["sha256_directory"]:
            raise ValueError(
                f"{artifact['model_id']}: directory SHA-256 mismatch "
                f"({actual_directory_hash} != {artifact['sha256_directory']})"
            )
        destination = args.output_dir / artifact["release_asset"]
        build_deterministic_archive(source, destination)
        packaged.append(
            {
                "model_id": artifact["model_id"],
                "asset": destination.name,
                "size_bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "source_directory_sha256": actual_directory_hash,
            }
        )

    output = {
        "schema": "glaciernet-kz.model-release-assets.v1",
        "version": manifest["version"],
        "artifacts": packaged,
    }
    checksum_path = args.output_dir / "model_release_checksums.json"
    checksum_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
