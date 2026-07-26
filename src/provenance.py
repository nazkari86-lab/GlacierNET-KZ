"""Reproducible provenance records for local prediction artifacts."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

PREDICTION_PROVENANCE_SCHEMA = "glaciernet-kz.prediction-provenance.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(path: Path) -> str:
    """Hash a directory deterministically, including relative filenames."""
    digest = hashlib.sha256()
    files = sorted(item for item in path.rglob("*") if item.is_file())
    if not files:
        raise ValueError(f"No files found under {path}")
    for item in files:
        relative = item.relative_to(path).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def sha256_artifact(path: Path) -> str:
    if path.is_dir():
        return sha256_directory(path)
    if path.is_file():
        return sha256_file(path)
    raise FileNotFoundError(f"Missing artifact: {path}")


def git_state(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"commit": commit, "working_tree_dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "working_tree_dirty": None}


def model_provenance(
    model_name: str,
    *,
    root: Path,
    prediction_dir: Path,
    ndsi_threshold: float,
    use_tta: bool,
) -> dict[str, Any]:
    mask_path = prediction_dir / f"{model_name}_mask.tif"
    if not mask_path.is_file():
        raise FileNotFoundError(f"Missing prediction mask: {mask_path}")

    record: dict[str, Any] = {
        "mask_file": str(mask_path.relative_to(root)),
        "mask_size_bytes": mask_path.stat().st_size,
        "mask_sha256": sha256_file(mask_path),
    }
    if model_name == "ndsi":
        record.update(
            {
                "method": "deterministic_threshold",
                "implementation": "predict.py:run_ndsi",
                "parameters": {"threshold": ndsi_threshold},
                "model_artifact": None,
            }
        )
        return record

    artifact_names = {
        "rf": "random_forest.pkl",
        "unet": "unet_best.h5",
    }
    artifact_name = artifact_names.get(model_name)
    if artifact_name is None:
        raise ValueError(f"Unsupported prediction model for provenance: {model_name}")
    artifact = root / "models" / artifact_name
    if not artifact.is_file():
        raise FileNotFoundError(f"Missing model artifact: {artifact}")
    record.update(
        {
            "method": "trained_model",
            "implementation": f"predict.py:run_{model_name}",
            "parameters": {"test_time_augmentation": use_tta} if model_name == "unet" else {},
            "model_artifact": str(artifact.relative_to(root)),
            "model_size_bytes": artifact.stat().st_size,
            "model_sha256": sha256_file(artifact),
        }
    )
    return record


def build_prediction_provenance(
    *,
    root: Path,
    year: int,
    source_path: Path,
    prediction_dir: Path,
    model_names: list[str],
    ndsi_threshold: float,
    use_tta: bool = False,
) -> dict[str, Any]:
    source_path = source_path.resolve()
    prediction_dir = prediction_dir.resolve()
    with rasterio.open(source_path) as dataset:
        source = {
            "file": str(source_path.relative_to(root)),
            "size_bytes": source_path.stat().st_size,
            "sha256": sha256_file(source_path),
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "transform": list(dataset.transform)[:6],
            "shape": [dataset.height, dataset.width],
            "bands": dataset.count,
            "dtypes": list(dataset.dtypes),
        }

    models = {
        name: model_provenance(
            name,
            root=root,
            prediction_dir=prediction_dir,
            ndsi_threshold=ndsi_threshold,
            use_tta=use_tta,
        )
        for name in sorted(model_names)
    }
    return {
        "schema": PREDICTION_PROVENANCE_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "year": year,
        "source": source,
        "models": models,
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "rasterio": rasterio.__version__,
        },
        "git": git_state(root),
    }


def merge_prediction_provenance(path: Path, new_record: dict[str, Any]) -> dict[str, Any]:
    merged = dict(new_record)
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
        if (
            isinstance(existing, dict)
            and existing.get("schema") == PREDICTION_PROVENANCE_SCHEMA
            and existing.get("year") == new_record.get("year")
            and existing.get("source", {}).get("sha256") == new_record.get("source", {}).get("sha256")
        ):
            merged["models"] = {**existing.get("models", {}), **new_record.get("models", {})}
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return merged
