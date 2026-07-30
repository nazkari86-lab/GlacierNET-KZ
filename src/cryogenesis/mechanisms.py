"""Validation for the fixed, unscored CryoGenesis mechanism catalogue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MECHANISM_IDS = (
    "temperature_surface_melt",
    "snow_precipitation_deficit",
    "thin_debris_enhancement",
    "thick_debris_insulation",
    "proglacial_lake_contact",
    "dynamic_acceleration",
    "terrain_shading",
    "fragmentation_geometry",
    "observation_or_label_artifact",
    "unresolved_mechanism",
)
_REQUIRED_FIELDS = {
    "id",
    "required_variables",
    "expected_signature",
    "contradictory_signature",
}
_FORBIDDEN_SCORE_FIELDS = {
    "score",
    "probability",
    "confidence",
    "rank",
    "likelihood",
}


def validate_mechanism_catalog(records: object) -> tuple[dict[str, Any], ...]:
    """Require the complete fixed catalogue and prohibit Release 2 scoring."""

    if not isinstance(records, list):
        raise ValueError("mechanism catalogue must be a JSON array")
    validated: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"mechanism {index} must be an object")
        missing = _REQUIRED_FIELDS.difference(record)
        if missing:
            raise ValueError(f"mechanism {index} missing fields: {', '.join(sorted(missing))}")
        forbidden = _FORBIDDEN_SCORE_FIELDS.intersection(record)
        if forbidden:
            raise ValueError(f"mechanism {record.get('id')} contains Release 1 score fields")
        if not isinstance(record["required_variables"], list):
            raise ValueError("required_variables must be a list")
        validated.append(record)

    identifiers = tuple(record["id"] for record in validated)
    if identifiers != MECHANISM_IDS:
        raise ValueError("mechanism catalogue IDs or order do not match Release 1")
    return tuple(validated)


def load_mechanism_catalog(path: Path) -> tuple[dict[str, Any], ...]:
    """Load and validate the catalogue from a caller-selected local path."""

    return validate_mechanism_catalog(json.loads(path.read_text(encoding="utf-8")))
