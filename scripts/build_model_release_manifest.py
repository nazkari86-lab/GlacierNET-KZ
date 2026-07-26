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
                "release_asset": f"glaciernet-kz-{model_id}.tar.gz",
                "publication_status": "local_verified_not_yet_release_asset",
            }
        )
    return {
        "schema": "glaciernet-kz.model-release.v1",
        "version": "0.3.0",
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
