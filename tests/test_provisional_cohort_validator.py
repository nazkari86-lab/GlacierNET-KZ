from __future__ import annotations

from scripts.validate_provisional_cohorts import validate


def test_committed_provisional_cohorts_are_honestly_labelled_and_hash_verified() -> None:
    assert validate() == []
