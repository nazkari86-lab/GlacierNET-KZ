#!/usr/bin/env python3
"""Fail closed when scientific claims lack evidence, scope, or a valid status."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "benchmarks/v2/claims_registry.json"


def validate() -> list[str]:
    errors: list[str] = []
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    allowed = set(payload.get("allowed_statuses", []))
    claims = payload.get("claims", [])
    if payload.get("schema") != "glaciernet-kz.claims-registry.v1":
        errors.append("invalid claims registry schema")
    if not isinstance(claims, list) or not claims:
        errors.append("claims registry must not be empty")
        return errors
    seen: set[str] = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        claim_id = str(claim.get("id", ""))
        if not claim_id or claim_id in seen:
            errors.append(f"{prefix}: claim id must be non-empty and unique")
        seen.add(claim_id)
        if claim.get("status") not in allowed:
            errors.append(f"{prefix}: invalid status")
        if not str(claim.get("claim", "")).strip() or not str(claim.get("scope", "")).strip():
            errors.append(f"{prefix}: claim and scope are required")
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}: at least one evidence path is required")
            continue
        for relative in evidence:
            path = ROOT / str(relative)
            if not path.is_file():
                errors.append(f"{prefix}: missing evidence path: {relative}")
        if claim.get("status") == "blocked_external_evidence" and claim.get("publishable_wording"):
            errors.append(f"{prefix}: blocked claims cannot define publishable wording")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("CLAIMS REGISTRY VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Claims registry valid: supported, refuted, and blocked claims are explicitly scoped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
