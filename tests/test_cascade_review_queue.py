from __future__ import annotations

from scripts.build_cascade_review_queue import build_rows


def test_hmaglof_records_remain_pending_until_primary_source_review() -> None:
    rows = build_rows()
    assert len(rows) == 58
    assert all(row["primary_source_verified"] == "false" for row in rows)
    assert all(row["eligible_for_strict_benchmark"] == "false" for row in rows)
    assert all(row["source_review_status"].endswith("primary_source_review") for row in rows)
