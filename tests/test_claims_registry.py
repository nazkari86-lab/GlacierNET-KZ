from __future__ import annotations

import json

from scripts.validate_claims_registry import REGISTRY, validate


def test_claims_registry_is_complete_and_fail_closed() -> None:
    assert validate() == []
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    statuses = {claim["status"] for claim in payload["claims"]}
    assert "supported_silver" in statuses
    assert "supported_provisional" in statuses
    assert "refuted_for_current_model" in statuses
    assert "blocked_external_evidence" in statuses
