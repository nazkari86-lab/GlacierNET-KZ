#!/usr/bin/env python3
"""Project a patch dataset to selected channels while preserving labels and splits."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_channel_indices(raw: str, channel_count: int) -> list[int]:
    indices: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            start_raw, stop_raw = token.split(":", 1)
            start = int(start_raw) if start_raw else 0
            stop = int(stop_raw) if stop_raw else channel_count
            indices.extend(range(start, stop))
        else:
            indices.append(int(token))
    if not indices:
        raise ValueError("At least one channel must be selected")
    if len(indices) != len(set(indices)):
        raise ValueError("Channel selection contains duplicates")
    if min(indices) < 0 or max(indices) >= channel_count:
        raise ValueError(f"Channel selection outside [0, {channel_count}): {indices}")
    return indices


def link_label(source: Path, destination: Path) -> None:
    if destination.exists():
        if destination.stat().st_ino == source.stat().st_ino:
            return
        raise FileExistsError(f"Refusing to replace existing label array: {destination}")
    os.link(source, destination)


def project_year(entry: dict, *, output_dir: Path, indices: list[int]) -> dict:
    source_dir = ROOT / entry["output_dir"]
    year_dir = output_dir / str(entry["year"])
    year_dir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        source_x = np.load(source_dir / f"X_{split}.npy", mmap_mode="r")
        if source_x.ndim != 4:
            raise ValueError(f"Expected rank-4 patch array: {source_dir / f'X_{split}.npy'}")
        np.save(year_dir / f"X_{split}.npy", np.asarray(source_x[..., indices], dtype=np.float32))
        link_label(source_dir / f"y_{split}.npy", year_dir / f"y_{split}.npy")
    return {
        **entry,
        "output_dir": str(year_dir.relative_to(ROOT)),
        "source_bands_loaded": len(indices),
        "channel_projection": indices,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--channels",
        required=True,
        help="Comma-separated indices and half-open ranges, for example 0:14 or 0:7,11:14",
    )
    args = parser.parse_args()

    source_path = args.source_manifest.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    channel_count = int(source["channel_count"])
    feature_schema = source.get("feature_schema")
    if not isinstance(feature_schema, list) or len(feature_schema) != channel_count:
        raise ValueError("Source manifest feature_schema must match channel_count")
    indices = parse_channel_indices(args.channels, channel_count)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        **source,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_role": "controlled_channel_ablation",
        "source_manifest": str(source_path.relative_to(ROOT)),
        "channel_count": len(indices),
        "feature_schema": [feature_schema[index] for index in indices],
        "channel_projection": indices,
        "projection_note": (
            "Feature arrays are projected from the exact same sampled patches and splits. "
            "Label arrays are local hardlinks to preserve byte identity without duplication."
        ),
        "years": [],
    }
    for entry in source["years"]:
        print(f"Projecting {entry['year']} to {len(indices)} channels...", flush=True)
        manifest["years"].append(project_year(entry, output_dir=output_dir, indices=indices))

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote projected manifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
