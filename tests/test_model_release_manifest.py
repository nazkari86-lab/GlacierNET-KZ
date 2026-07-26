from __future__ import annotations

import json

from scripts.build_model_release_manifest import MODELS, OUTPUT, ROOT, build_manifest


def test_release_manifest_covers_verified_benchmark_models() -> None:
    manifest = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert manifest["doi"] is None
    assert len(manifest["artifacts"]) == len(MODELS) == 3
    for artifact in manifest["artifacts"]:
        assert artifact["size_bytes"] > 90_000_000
        assert len(artifact["sha256_directory"]) == 64
        assert len(artifact["evaluation_report_sha256"]) == 64
        assert artifact["publication_status"] == "local_verified_not_yet_release_asset"

    # The git checkout intentionally excludes 276+ MB of model weights. Rebuild
    # and compare only in a hydrated workspace where all artifacts exist.
    if all((ROOT / relative_model).is_dir() for _, relative_model, _ in MODELS):
        assert build_manifest() == manifest
