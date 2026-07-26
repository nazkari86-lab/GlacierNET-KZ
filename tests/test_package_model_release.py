from __future__ import annotations

import tarfile
from pathlib import Path

from scripts.package_model_release import build_deterministic_archive
from src.provenance import sha256_file


def test_model_archive_is_deterministic_and_normalized(tmp_path: Path) -> None:
    source = tmp_path / "model"
    source.mkdir()
    (source / "saved_model.pb").write_bytes(b"model")
    variables = source / "variables"
    variables.mkdir()
    (variables / "variables.index").write_bytes(b"index")

    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    build_deterministic_archive(source, first)
    build_deterministic_archive(source, second)

    assert sha256_file(first) == sha256_file(second)
    with tarfile.open(first, "r:gz") as archive:
        assert archive.getnames() == [
            "model",
            "model/saved_model.pb",
            "model/variables",
            "model/variables/variables.index",
        ]
        assert all(member.mtime == 0 for member in archive.getmembers())
        assert all(member.uid == 0 and member.gid == 0 for member in archive.getmembers())
