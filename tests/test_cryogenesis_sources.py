from pathlib import Path

import pytest

from src.cryogenesis.source_registry import RegisteredSource, verify_sources


def test_missing_or_changed_source_blocks_cohort(tmp_path: Path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"physical")
    source = RegisteredSource.from_path("source", path, tmp_path)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        verify_sources((source,), tmp_path)
