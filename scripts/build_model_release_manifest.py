#!/usr/bin/env python3
"""Build a deterministic release manifest for the three benchmark SavedModels."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.provenance import sha256_directory, sha256_file  # noqa: E402

OUTPUT = ROOT / "releases/model_artifacts.v1.json"
RELEASE_TAG = "v0.3.0"
RELEASE_URL = "https://github.com/nazkari86-lab/GlacierNET-KZ/releases/tag/v0.3.0"
RELEASE_COMMIT = "8a2ff4c30156eed14dc4bb2b30ee6813a5316883"
RELEASE_ASSETS = {
    "s2_terrain_14ch": {
        "size_bytes": 87129304,
        "sha256": "7045bf4c9f436a4fefc922c916a2135135d3593af8c3b8bac173a6b405173fda",
    },
    "compact_s2_terrain_control": {
        "size_bytes": 86530971,
        "sha256": "cf52e0b1060bc364f6badfa40cb3dc66f19e52e3d54285f78a8021804dab051f",
    },
    "compact_s2_terrain_s1": {
        "size_bytes": 86779400,
        "sha256": "ead222a776494605f663f1eedacc1bf126efd13af21b5f18abad6c62d0148ca8",
    },
}
MODELS = (
    (
        "s2_terrain_14ch",
        "models/unet_best_sentinel2_terrain_year_holdout_2016_2024",
        "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json",
    ),
    (
        "compact_s2_terrain_control",
        "models/unet_best_sentinel2_terrain_control_year_holdout_2017_2024",
        "results/ablation_unet_sentinel2_terrain_control_2017_2024.json",
    ),
    (
        "compact_s2_terrain_s1",
        "models/unet_best_sentinel2_terrain_s1_year_holdout_2017_2024",
        "results/ablation_unet_sentinel2_terrain_s1_2017_2024.json",
    ),
)


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def build_manifest() -> dict[str, object]:
    trusted = json.loads((ROOT / "models/trusted_artifacts.json").read_text(encoding="utf-8"))["artifacts"]
    artifacts: list[dict[str, object]] = []
    for model_id, relative_model, relative_report in MODELS:
        model_path = ROOT / relative_model
        report_path = ROOT / relative_report
        release_asset = f"glaciernet-kz-{model_id}.tar.gz"
        published = RELEASE_ASSETS[model_id]
        digest = sha256_directory(model_path)
        if trusted.get(relative_model) != digest:
            raise ValueError(f"trusted digest mismatch: {relative_model}")
        artifacts.append(
            {
                "model_id": model_id,
                "local_path": relative_model,
                "format": "TensorFlow SavedModel",
                "size_bytes": directory_size(model_path),
                "sha256_directory": digest,
                "evaluation_report": relative_report,
                "evaluation_report_sha256": sha256_file(report_path),
                "release_asset": release_asset,
                "release_asset_url": (
                    f"https://github.com/nazkari86-lab/GlacierNET-KZ/releases/download/{RELEASE_TAG}/{release_asset}"
                ),
                "release_asset_size_bytes": published["size_bytes"],
                "release_asset_sha256": published["sha256"],
                "publication_status": "github_release_verified",
            }
        )
    return {
        "schema": "glaciernet-kz.model-release.v1",
        "version": "0.3.0",
        "release_tag": RELEASE_TAG,
        "release_url": RELEASE_URL,
        "release_commit": RELEASE_COMMIT,
        "artifacts": artifacts,
        "doi": None,
        "doi_status": "not_minted",
        "claim_boundary": "One-AOI RGI-derived silver benchmark; no gold or external-region claim.",
    }


def main() -> int:
    payload = build_manifest()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload['artifacts'])} model records to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
