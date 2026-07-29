#!/usr/bin/env python3
"""Render a compact visual QA sheet for enhanced provisional annotations."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.plot import plotting_extent
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "benchmarks/v2/annotations/enhanced_provisional"
OUTPUT = PACK / "annotation_qa_contact_sheet.png"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stretch(rgb: np.ndarray) -> np.ndarray:
    result = np.zeros_like(rgb, dtype=np.float32)
    for index in range(3):
        values = rgb[index]
        finite = values[np.isfinite(values)]
        low, high = np.percentile(finite, (2, 98)) if finite.size else (0, 1)
        result[index] = np.clip((values - low) / max(high - low, 1e-6), 0, 1)
    return np.moveaxis(result, 0, -1)


def main() -> int:
    with (PACK / "enhanced_annotation_queue.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    high = sorted(
        (row for row in rows if row["confidence"] == "high_provisional"),
        key=lambda row: float(row["quality_score"]),
        reverse=True,
    )[:3]
    review = sorted(
        (row for row in rows if row["confidence"] == "low_provisional"),
        key=lambda row: int(row["review_priority"]),
        reverse=True,
    )[:3]
    selected = high + review

    figure, axes = plt.subplots(2, 3, figsize=(15, 10), constrained_layout=True)
    for axis, row in zip(axes.ravel(), selected, strict=True):
        year = int(row["year"])
        glacier_id = row["glacier_id"]
        gpkg = PACK / f"enhanced_labels_{year}.gpkg"
        labels = gpd.read_file(gpkg, layer="glacier_labels")
        reviews = gpd.read_file(gpkg, layer="review_zones")
        label = labels[labels["glacier_id"] == glacier_id]
        review_zone = reviews[reviews["glacier_id"] == glacier_id]
        bounds_source = review_zone if not review_zone.empty else label
        minx, miny, maxx, maxy = bounds_source.total_bounds
        pad = max(150.0, 0.12 * max(maxx - minx, maxy - miny))
        source_path = ROOT / f"data/raw/sentinel2/sentinel2_{year}.tif"
        with rasterio.open(source_path) as source:
            window = from_bounds(minx - pad, miny - pad, maxx + pad, maxy + pad, source.transform)
            window = window.round_offsets().round_lengths()
            rgb = source.read([3, 2, 1], window=window, boundless=True, fill_value=0)
            transform = source.window_transform(window)
            extent = plotting_extent(rgb[0], transform)
        axis.imshow(stretch(rgb), extent=extent)
        if not review_zone.empty:
            review_zone.boundary.plot(ax=axis, color="#ff9f1c", linewidth=1.4, linestyle="--")
        if not label.empty and not label.geometry.is_empty.all():
            label.boundary.plot(ax=axis, color="#00d4ff", linewidth=2.0)
        axis.set_title(
            f"{glacier_id.split('-')[-1]} · {year}\n"
            f"{row['confidence']} · Q={float(row['quality_score']):.1f} · review={row['review_priority']}",
            fontsize=10,
        )
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_facecolor("#101820")
    figure.suptitle(
        "GlacierNET-KZ annotation QA · cyan label / orange mandatory review\n"
        "Top 3 high-confidence and top 3 review-priority cases",
        fontsize=15,
        fontweight="bold",
    )
    figure.savefig(OUTPUT, dpi=170, facecolor="white")
    plt.close(figure)

    manifest_path = PACK / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["qa_preview"] = {
        "path": str(OUTPUT.relative_to(ROOT)),
        "sha256": sha256(OUTPUT),
        "size_bytes": OUTPUT.stat().st_size,
        "cases": [
            {"glacier_id": row["glacier_id"], "year": int(row["year"]), "confidence": row["confidence"]}
            for row in selected
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered annotation QA sheet: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
