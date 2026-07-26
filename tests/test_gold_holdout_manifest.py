from __future__ import annotations

import pytest

from scripts.build_glacier_holdout_manifest import validate_gold_rows


def _row() -> dict[str, str]:
    return {
        "glacier_id": "g1",
        "region": "Ile Alatau",
        "year": "2024",
        "annotator_a": "expert-a",
        "annotator_b": "expert-b",
        "adjudicator": "expert-c",
        "annotation_status": "adjudicated",
        "label_sha256": "a" * 64,
    }


def test_gold_rows_require_two_independent_annotators() -> None:
    row = _row()
    row["annotator_b"] = row["annotator_a"]
    with pytest.raises(ValueError, match="two distinct"):
        validate_gold_rows([row])


def test_gold_rows_require_adjudication_and_digest() -> None:
    row = _row()
    row["annotation_status"] = "pending"
    with pytest.raises(ValueError, match="adjudicated"):
        validate_gold_rows([row])
    row = _row()
    row["label_sha256"] = ""
    with pytest.raises(ValueError, match="SHA-256"):
        validate_gold_rows([row])


def test_complete_gold_row_is_accepted() -> None:
    validate_gold_rows([_row()])
