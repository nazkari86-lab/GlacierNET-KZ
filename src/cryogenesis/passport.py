"""Canonical construction and fail-closed verification of Discovery Passports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from typing import Any

from .schemas import (
    DiscoveryPassport,
    DivergenceResult,
    MatchResult,
    SourceAsset,
    SurpriseClass,
    VerificationResult,
)

PASSPORT_SCHEMA = "glaciernet-kz.cryogenesis-passport.v1"
CLAIM_TIERS = (
    "cohort_built",
    "comparison_valid",
    "divergence_measured",
    "hypothesis_screened",
    "temporally_replicated",
    "spatially_replicated",
    "externally_replicated",
    "field_consistent",
    "mechanism_candidate",
)
CLAIMS_ALLOWED = (
    "retrospective mapped-area comparison",
    "auditable matched-comparator association",
    "evidence-gap prioritisation",
)
CLAIMS_NOT_ALLOWED = (
    "causal effect identification",
    "mass or volume loss",
    "calibrated GLOF probability",
    "operational warning",
    "validated intervention recommendation",
    "prospective forecast",
)

_REQUIRED_FIELDS = {
    "schema",
    "cohort_id",
    "target_rgi_id",
    "claim_tier",
    "match",
    "divergence",
    "surprise_class",
    "claims_allowed",
    "claims_not_allowed",
    "provenance",
    "payload_sha256",
}


def canonical_bytes(payload: dict[str, object]) -> bytes:
    """Encode a JSON object identically across runs and platforms."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _json_compatible(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _payload_digest(payload: dict[str, object]) -> str:
    unsigned = dict(payload)
    unsigned.pop("payload_sha256", None)
    return hashlib.sha256(canonical_bytes(unsigned)).hexdigest()


def build_passport(
    *,
    cohort_id: str,
    target_rgi_id: str,
    match: MatchResult,
    divergence: DivergenceResult | None,
    surprise_class: SurpriseClass,
    provenance: tuple[SourceAsset, ...],
) -> DiscoveryPassport:
    """Construct and content-address one Release 1 passport."""

    if not cohort_id:
        raise ValueError("cohort_id must not be empty")
    if match.target_rgi_id != target_rgi_id:
        raise ValueError("match target_rgi_id does not match passport target")
    if not provenance:
        raise ValueError("provenance must contain at least one source asset")

    passport = DiscoveryPassport(
        schema=PASSPORT_SCHEMA,
        cohort_id=cohort_id,
        target_rgi_id=target_rgi_id,
        claim_tier="cohort_built",
        match=match,
        divergence=divergence,
        surprise_class=surprise_class,
        claims_allowed=CLAIMS_ALLOWED,
        claims_not_allowed=CLAIMS_NOT_ALLOWED,
        provenance=provenance,
    )
    payload = _json_compatible(asdict(passport))
    return replace(passport, payload_sha256=_payload_digest(payload))


def passport_to_dict(passport: DiscoveryPassport) -> dict[str, Any]:
    """Return a JSON-compatible object without losing canonical ordering."""

    return _json_compatible(asdict(passport))


def verify_passport(payload: dict[str, Any]) -> VerificationResult:
    """Validate schema, policy and content digest without recalculating science."""

    errors: list[str] = []
    missing = sorted(_REQUIRED_FIELDS.difference(payload))
    if missing:
        errors.extend(f"missing:{field}" for field in missing)

    if payload.get("schema") != PASSPORT_SCHEMA:
        errors.append("schema")
    if payload.get("claim_tier") not in CLAIM_TIERS:
        errors.append("claim_tier")

    target_rgi_id = payload.get("target_rgi_id")
    match = payload.get("match")
    if not isinstance(match, dict) or match.get("target_rgi_id") != target_rgi_id:
        errors.append("match.target_rgi_id")

    claims_allowed = payload.get("claims_allowed")
    claims_not_allowed = payload.get("claims_not_allowed")
    if not isinstance(claims_allowed, list) or any(claim in CLAIMS_NOT_ALLOWED for claim in claims_allowed):
        errors.append("claims_allowed")
    if not isinstance(claims_not_allowed, list) or not set(CLAIMS_NOT_ALLOWED).issubset(claims_not_allowed):
        errors.append("claims_not_allowed")

    provenance = payload.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        errors.append("provenance")
    else:
        for index, source in enumerate(provenance):
            digest = source.get("sha256") if isinstance(source, dict) else None
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                errors.append(f"provenance[{index}].sha256")

    supplied_digest = payload.get("payload_sha256")
    if not isinstance(supplied_digest, str) or supplied_digest != _payload_digest(payload):
        errors.append("payload_sha256")

    return VerificationResult(valid=not errors, errors=tuple(errors))
