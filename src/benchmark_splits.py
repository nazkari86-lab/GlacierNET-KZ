"""Leakage-resistant glacier-level split utilities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np


def glacier_holdout_split(
    glacier_ids: Iterable[str],
    *,
    train_ratio: float = 0.6,
    validation_ratio: float = 0.2,
    test_ratio: float = 0.2,
    seed: int = 42,
) -> dict[str, Any]:
    """Assign every unique glacier to exactly one deterministic split."""
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(ratio <= 0 for ratio in ratios) or not np.isclose(sum(ratios), 1.0):
        raise ValueError("split ratios must be positive and sum to 1")
    glaciers = sorted({str(value).strip() for value in glacier_ids if str(value).strip()})
    if len(glaciers) < 5:
        raise ValueError("at least five unique glacier IDs are required")

    shuffled = np.asarray(glaciers, dtype=object)
    np.random.default_rng(seed).shuffle(shuffled)
    n = len(shuffled)
    train_end = max(1, int(np.floor(n * train_ratio)))
    validation_end = train_end + max(1, int(np.floor(n * validation_ratio)))
    if validation_end >= n:
        validation_end = n - 1
    manifest = {
        "split_strategy": "glacier_holdout",
        "grouping_key": "glacier_id",
        "seed": seed,
        "train_glaciers": sorted(shuffled[:train_end].tolist()),
        "validation_glaciers": sorted(shuffled[train_end:validation_end].tolist()),
        "test_glaciers": sorted(shuffled[validation_end:].tolist()),
    }
    validate_group_manifest(manifest)
    return manifest


def cross_region_split(
    glacier_regions: Mapping[str, str],
    *,
    train_region: str,
    test_region: str,
) -> dict[str, Any]:
    """Build a strict train-region versus external-test-region manifest."""
    if train_region == test_region:
        raise ValueError("train_region and test_region must differ")
    train = sorted(glacier for glacier, region in glacier_regions.items() if region == train_region)
    test = sorted(glacier for glacier, region in glacier_regions.items() if region == test_region)
    if not train or not test:
        raise ValueError("both train and external test regions require glacier IDs")
    manifest = {
        "split_strategy": "cross_region",
        "grouping_key": "glacier_id",
        "train_region": train_region,
        "test_region": test_region,
        "train_glaciers": train,
        "validation_glaciers": [],
        "test_glaciers": test,
    }
    validate_group_manifest(manifest, require_validation=False)
    return manifest


def validate_group_manifest(manifest: Mapping[str, Any], *, require_validation: bool = True) -> None:
    """Fail closed when glacier IDs overlap or required groups are empty."""
    required = ("train_glaciers", "validation_glaciers", "test_glaciers")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise ValueError(f"missing split fields: {missing}")
    groups = {key: [str(value) for value in manifest[key]] for key in required}
    if not groups["train_glaciers"] or not groups["test_glaciers"]:
        raise ValueError("train and test glacier groups must be non-empty")
    if require_validation and not groups["validation_glaciers"]:
        raise ValueError("validation glacier group must be non-empty")
    for key, values in groups.items():
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate glacier IDs in {key}")
    pairs = (
        ("train_glaciers", "validation_glaciers"),
        ("train_glaciers", "test_glaciers"),
        ("validation_glaciers", "test_glaciers"),
    )
    for left, right in pairs:
        overlap = set(groups[left]) & set(groups[right])
        if overlap:
            raise ValueError(f"glacier leakage between {left} and {right}: {sorted(overlap)}")
