"""Fail-closed verification for model artifacts loaded by GlacierNET-KZ."""

from __future__ import annotations

import json
from pathlib import Path

from src.provenance import sha256_artifact

TRUST_SCHEMA = "glaciernet-kz.trusted-models.v1"


def verify_trusted_model(model_path: Path, *, root: Path) -> str:
    """Verify a local model against the versioned SHA-256 trust registry."""
    root = root.resolve()
    requested_path = model_path
    if requested_path.is_symlink() or any(item.is_symlink() for item in requested_path.rglob("*")):
        raise ValueError(f"Model artifact contains a symlink: {requested_path}")

    resolved = requested_path.resolve(strict=True)
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Model artifact is outside the project root: {resolved}") from exc

    registry_path = root / "models" / "trusted_artifacts.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != TRUST_SCHEMA or not isinstance(registry.get("artifacts"), dict):
        raise ValueError(f"Invalid trusted-model registry: {registry_path}")

    expected = registry["artifacts"].get(relative)
    if not isinstance(expected, str):
        raise ValueError(
            f"Untrusted model artifact: {relative}. Register its reviewed SHA-256 before deserializing it."
        )
    actual = sha256_artifact(resolved)
    if actual != expected:
        raise ValueError(f"Model artifact SHA-256 mismatch for {relative}: expected {expected}, got {actual}")
    return actual
