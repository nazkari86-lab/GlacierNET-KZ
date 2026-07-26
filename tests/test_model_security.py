import json
from pathlib import Path

import pytest

from src.model_security import TRUST_SCHEMA, verify_trusted_model
from src.provenance import sha256_artifact


def _registry(root: Path, artifact: Path, digest: str) -> None:
    models = root / "models"
    models.mkdir()
    (models / "trusted_artifacts.json").write_text(
        json.dumps(
            {
                "schema": TRUST_SCHEMA,
                "artifacts": {artifact.relative_to(root).as_posix(): digest},
            }
        ),
        encoding="utf-8",
    )


def test_trusted_artifact_exact_hash_passes(tmp_path: Path):
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"reviewed model")
    _registry(tmp_path, artifact, sha256_artifact(artifact))
    assert verify_trusted_model(artifact, root=tmp_path) == sha256_artifact(artifact)


def test_modified_artifact_fails_closed(tmp_path: Path):
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"reviewed model")
    _registry(tmp_path, artifact, sha256_artifact(artifact))
    artifact.write_bytes(b"modified model")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_trusted_model(artifact, root=tmp_path)


def test_unregistered_artifact_fails_closed(tmp_path: Path):
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"unregistered")
    _registry(tmp_path, artifact, "0" * 64)
    (tmp_path / "other.bin").write_bytes(b"other")
    with pytest.raises(ValueError, match="Untrusted model"):
        verify_trusted_model(tmp_path / "other.bin", root=tmp_path)
