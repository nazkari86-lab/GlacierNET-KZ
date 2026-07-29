#!/usr/bin/env python3
"""Record the final on-disk QGIS project checksum after QGIS has closed."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "benchmarks/v2/annotations/enhanced_provisional"
PROJECT = PACK / "GlacierNET-KZ_Annotation_Workspace.qgz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if not PROJECT.is_file():
        raise FileNotFoundError(PROJECT)
    with zipfile.ZipFile(PROJECT) as archive:
        project_files = [name for name in archive.namelist() if name.endswith(".qgs")]
        if len(project_files) != 1:
            raise ValueError("QGZ must contain exactly one QGS project")
        document = ElementTree.fromstring(archive.read(project_files[0]))
        layer_count = len(document.findall(".//projectlayers/maplayer"))
    manifest_path = PACK / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["qgis_project"] = {
        "path": str(PROJECT.relative_to(ROOT)),
        "sha256": sha256(PROJECT),
        "size_bytes": PROJECT.stat().st_size,
        "layer_count": layer_count,
        "source_rasters_duplicated": False,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Finalized QGIS project manifest: {layer_count} layers, {manifest['qgis_project']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
