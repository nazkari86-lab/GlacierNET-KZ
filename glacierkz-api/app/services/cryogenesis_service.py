"""Read-only access to validated, saved CryoGenesis artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.utils import resolve_core_dir
from src.cryogenesis.passport import CLAIMS_NOT_ALLOWED, verify_passport

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")


def resolve_project_root() -> Path:
    configured = resolve_core_dir(__file__).resolve()
    for candidate in (configured, configured.parent):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return configured


PROJECT_ROOT = resolve_project_root()
CRYOGENESIS_ROOT = PROJECT_ROOT / "results" / "cryogenesis" / "current"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must contain a JSON object: {path.name}")
    return payload


def _passport_path(rgi_id: str) -> Path:
    if not _SAFE_ID.fullmatch(rgi_id):
        raise ValueError("invalid glacier ID")
    root = CRYOGENESIS_ROOT.resolve()
    path = (root / "passports" / f"{rgi_id}.json").resolve()
    if not path.is_relative_to(root):
        raise ValueError("passport path escapes artifact root")
    return path


def get_passport(
    rgi_id: str,
    cohort_id: str | None = None,
) -> dict[str, Any]:
    path = _passport_path(rgi_id)
    if not path.is_file():
        raise FileNotFoundError(rgi_id)
    try:
        payload = _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {
            "status": "invalid_artifact",
            "rgi_id": rgi_id,
            "reason": str(error),
            "claims_not_allowed": list(CLAIMS_NOT_ALLOWED),
        }
    if cohort_id is not None and payload.get("cohort_id") != cohort_id:
        raise FileNotFoundError(f"{rgi_id}:{cohort_id}")
    verification = verify_passport(payload)
    if not verification.valid:
        return {
            "status": "invalid_artifact",
            "rgi_id": rgi_id,
            "reason": "passport verification failed",
            "verification_errors": list(verification.errors),
            "claims_not_allowed": list(CLAIMS_NOT_ALLOWED),
        }
    return payload


def list_cohorts() -> dict[str, Any]:
    manifest_path = CRYOGENESIS_ROOT / "manifest.json"
    if not manifest_path.is_file():
        return {"status": "unavailable", "items": [], "count": 0}
    try:
        manifest = _read_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return {
            "status": "invalid_artifact",
            "items": [],
            "count": 0,
            "reason": str(error),
        }
    return {"status": "ready", "items": [manifest], "count": 1}


def discovery_status() -> dict[str, Any]:
    cohorts = list_cohorts()
    passport_root = CRYOGENESIS_ROOT / "passports"
    return {
        "status": cohorts["status"],
        "cohort_count": cohorts["count"],
        "passport_file_count": (len(list(passport_root.glob("*.json"))) if passport_root.is_dir() else 0),
        "claims_not_allowed": list(CLAIMS_NOT_ALLOWED),
    }


def list_discoveries(
    *,
    cohort_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    passport_root = CRYOGENESIS_ROOT / "passports"
    if not passport_root.is_dir():
        return {
            "status": "unavailable",
            "items": [],
            "count": 0,
            "invalid_artifact_count": 0,
        }
    items: list[dict[str, Any]] = []
    invalid_count = 0
    for path in sorted(passport_root.glob("*.json")):
        try:
            payload = get_passport(path.stem, cohort_id)
        except FileNotFoundError:
            continue
        if payload.get("status") == "invalid_artifact":
            invalid_count += 1
            continue
        if status is not None and status not in {
            payload.get("surprise_class"),
            payload.get("match", {}).get("status"),
        }:
            continue
        divergence = payload.get("divergence")
        match = payload.get("match", {})
        items.append(
            {
                "schema": "glaciernet-kz.cryogenesis-discovery-summary.v1",
                "cohort_id": payload["cohort_id"],
                "target_rgi_id": payload["target_rgi_id"],
                "claim_tier": payload["claim_tier"],
                "match_status": match.get("status"),
                "twin_count": len(match.get("twins", [])),
                "surprise_class": payload["surprise_class"],
                "raw_divergence": (divergence.get("raw_divergence") if isinstance(divergence, dict) else None),
                "payload_sha256": payload["payload_sha256"],
            }
        )
        if len(items) >= limit:
            break
    return {
        "status": "ready",
        "items": items,
        "count": len(items),
        "invalid_artifact_count": invalid_count,
    }
