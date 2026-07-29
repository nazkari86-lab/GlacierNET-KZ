#!/usr/bin/env python3
"""Build a multi-evidence, editable glacier annotation pack for QGIS.

The pack is deliberately labelled ``enhanced_provisional`` rather than gold.
It derives annual candidate geometry from each year's original Sentinel-2
stack, uses RGI only as a spatial prior, measures temporal agreement, and
separates uncertain pixels into an explicit review layer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize, shapes
from rasterio.windows import Window, from_bounds
from rasterio.windows import transform as window_transform
from scipy import ndimage
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP = ROOT / "benchmarks/v2/annotations/machine_assisted/rgi_inventory_provisional_2024.gpkg"
DEFAULT_OUTPUT = ROOT / "benchmarks/v2/annotations/enhanced_provisional"
LABEL_TIER = "enhanced_provisional_multievidence"
SCHEMA = "glaciernet-kz.enhanced-provisional-annotations.v1"
PIXEL_AREA_M2 = 100.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def clamp_window(window: Window, width: int, height: int) -> Window:
    col_off = max(0, int(math.floor(window.col_off)))
    row_off = max(0, int(math.floor(window.row_off)))
    col_end = min(width, int(math.ceil(window.col_off + window.width)))
    row_end = min(height, int(math.ceil(window.row_off + window.height)))
    return Window(col_off, row_off, max(0, col_end - col_off), max(0, row_end - row_off))


def remove_small_components(mask: np.ndarray, minimum_pixels: int) -> np.ndarray:
    labelled, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(labelled.ravel())
    keep = sizes >= minimum_pixels
    keep[0] = False
    return keep[labelled]


def normalize_reflectance(values: np.ndarray) -> np.ndarray:
    finite = values[np.isfinite(values)]
    if finite.size and float(np.nanpercentile(finite, 99)) > 2:
        return values / 10_000.0
    return values


def polygonal(geometry: Any) -> Polygon | MultiPolygon:
    fixed = make_valid(geometry)
    if isinstance(fixed, (Polygon, MultiPolygon)):
        return fixed
    if isinstance(fixed, GeometryCollection):
        polygons = [part for part in fixed.geoms if isinstance(part, (Polygon, MultiPolygon))]
        if polygons:
            merged = unary_union(polygons)
            if isinstance(merged, (Polygon, MultiPolygon)):
                return merged
    return Polygon()


def mask_to_geometry(mask: np.ndarray, transform: rasterio.Affine) -> Polygon | MultiPolygon:
    geometries = [
        shape(item) for item, value in shapes(mask.astype(np.uint8), mask=mask, transform=transform) if int(value) == 1
    ]
    if not geometries:
        return Polygon()
    return polygonal(unary_union(geometries).simplify(2.0, preserve_topology=True))


def iou(left: np.ndarray, right: np.ndarray) -> float:
    union = np.logical_or(left, right).sum()
    return float(np.logical_and(left, right).sum() / union) if union else 0.0


def annual_evidence(
    *,
    ndsi: np.ndarray,
    green: np.ndarray,
    valid: np.ndarray,
    temporal_clean_fraction: np.ndarray,
    rgi_mask: np.ndarray,
    target_zone: np.ndarray,
    pixel_size_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return conservative label, review zone and continuous evidence score."""
    annual_strength = np.clip((ndsi - 0.20) / 0.45, 0.0, 1.0)
    green_support = np.clip((green - 0.06) / 0.18, 0.0, 1.0)
    spectral_strength = 0.82 * annual_strength + 0.18 * green_support
    score = 0.55 * spectral_strength + 0.20 * temporal_clean_fraction + 0.25 * rgi_mask

    distance_outside = ndimage.distance_transform_edt(~rgi_mask) * pixel_size_m
    admissible = target_zone & np.logical_or(rgi_mask, distance_outside <= 70.0)
    candidate = (score >= 0.60) & valid & admissible
    candidate = ndimage.binary_closing(candidate, structure=np.ones((3, 3), dtype=bool))
    candidate = ndimage.binary_opening(candidate, structure=np.ones((2, 2), dtype=bool))
    candidate = remove_small_components(candidate, minimum_pixels=5)

    # Keep only components that have defensible contact with the target RGI
    # body. This prevents persistent seasonal snow in the outer buffer from
    # becoming a standalone glacier polygon.
    components, count = ndimage.label(candidate, structure=np.ones((3, 3), dtype=np.uint8))
    retained = np.zeros_like(candidate, dtype=bool)
    for component_id in range(1, count + 1):
        component = components == component_id
        if np.logical_and(component, rgi_mask).sum() >= 3:
            retained |= component
    candidate = retained

    boundary = np.logical_xor(
        ndimage.binary_dilation(candidate, iterations=2),
        ndimage.binary_erosion(candidate, iterations=2),
    )
    disagreement = np.logical_xor(candidate, rgi_mask)
    ambiguous_score = (score >= 0.38) & (score < 0.72)
    review = target_zone & (boundary | disagreement | ambiguous_score | ~valid)
    review = ndimage.binary_closing(review, structure=np.ones((3, 3), dtype=bool))
    review = remove_small_components(review, minimum_pixels=3)
    return candidate, review, score


def confidence_label(score: float, flags: list[str]) -> str:
    high_blockers = {
        "empty_candidate",
        "very_low_rgi_iou",
        "low_rgi_iou",
        "very_large_area_delta",
        "large_area_delta",
        "low_spectral_support",
        "temporal_disagreement",
        "missing_or_invalid_pixels",
        "large_review_zone",
    }
    low_triggers = {
        "empty_candidate",
        "very_low_rgi_iou",
        "very_large_area_delta",
        "low_spectral_support",
    }
    if score >= 82 and not high_blockers.intersection(flags):
        return "high_provisional"
    if score >= 62 and not low_triggers.intersection(flags):
        return "medium_provisional"
    return "low_provisional"


def qml_styles(output: Path) -> None:
    (output / "labels.qml").write_text(
        """<!DOCTYPE qgis>
<qgis version="4.0.2" styleCategories="Symbology|Labeling">
  <renderer-v2 type="singleSymbol">
    <symbols><symbol type="fill" name="0">
      <layer class="SimpleFill">
        <Option type="Map"><Option name="color" value="0,200,255,65"/><Option name="outline_color" value="0,105,148,255"/><Option name="outline_width" value="0.8"/></Option>
      </layer>
    </symbol></symbols>
  </renderer-v2>
  <labeling type="simple"><settings><text-style fieldName="glacier_id" isExpression="0"/></settings></labeling>
</qgis>
""",
        encoding="utf-8",
    )
    (output / "review_zones.qml").write_text(
        """<!DOCTYPE qgis>
<qgis version="4.0.2" styleCategories="Symbology">
  <renderer-v2 type="singleSymbol">
    <symbols><symbol type="fill" name="0">
      <layer class="SimpleFill">
        <Option type="Map"><Option name="color" value="255,170,0,45"/><Option name="outline_color" value="230,110,0,255"/><Option name="outline_style" value="dash"/><Option name="outline_width" value="0.6"/></Option>
      </layer>
    </symbol></symbols>
  </renderer-v2>
</qgis>
""",
        encoding="utf-8",
    )


def write_qgis_readme(output: Path, years: list[int]) -> None:
    source_lines = "\n".join(f"- `{relative(ROOT / f'data/raw/sentinel2/sentinel2_{year}.tif')}`" for year in years)
    (output / "README_QGIS.md").write_text(
        f"""# GlacierNET-KZ enhanced provisional annotation workspace

These files are machine-assisted starting geometries, **not gold labels**.

## Open in QGIS

1. Add the original annual Sentinel-2 stacks:
{source_lines}
2. For each year add `enhanced_labels_YYYY.gpkg` layer `glacier_labels`.
3. Add `enhanced_labels_YYYY.gpkg` layer `review_zones`.
4. Load `labels.qml` on label layers and `review_zones.qml` on review layers.
5. Display Sentinel bands B4/B3/B2 as RGB, then inspect NDSI (band 8), DEM,
   Sentinel-1 and adjacent years before editing.
6. Filter `review_priority >= 50` first. Every amber zone requires visual QA.
7. Save human work into a new `pass_1.gpkg`; never overwrite these generated files.

## Meaning of the layers

- `glacier_labels`: conservative annual candidate connected to the target RGI body.
- `review_zones`: boundary disagreement, ambiguous spectral evidence, missing pixels,
  and RGI-vs-annual differences that require a person.
- `label_classes_YYYY.tif`: 0 background, 1 provisional glacier, 2 review-only.

The source RGI geometry is a spatial prior, not annual ground truth. Existing
`data/processed/masks/mask_YYYY.tif` files were excluded because their SHA-256
digests are identical across years.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", type=Path, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024])
    parser.add_argument("--buffer-m", type=float, default=120.0)
    args = parser.parse_args()

    years = sorted(set(args.years))
    if len(years) < 2:
        parser.error("at least two years are required for temporal agreement")
    if not args.bootstrap.is_file():
        raise FileNotFoundError(args.bootstrap)
    sources = {year: ROOT / f"data/raw/sentinel2/sentinel2_{year}.tif" for year in years}
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing Sentinel-2 sources: {missing}")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    selected = gpd.read_file(args.bootstrap, layer="glacier_labels").to_crs(32642)
    selected = selected.sort_values("rgi_id").reset_index(drop=True)

    datasets = {year: rasterio.open(path) for year, path in sources.items()}
    reference = datasets[years[0]]
    for year, dataset in datasets.items():
        if dataset.crs != reference.crs or dataset.transform != reference.transform or dataset.shape != reference.shape:
            raise ValueError(f"Sentinel-2 source grid mismatch for {year}")
        if dataset.count < 11:
            raise ValueError(f"Sentinel-2 source for {year} has {dataset.count} bands; expected 11")

    generated: list[Path] = []
    queue_rows: list[dict[str, Any]] = []
    label_rows: dict[int, list[dict[str, Any]]] = {year: [] for year in years}
    review_rows: dict[int, list[dict[str, Any]]] = {year: [] for year in years}
    raster_paths = {year: output / f"label_classes_{year}.tif" for year in years}
    raster_arrays = {year: np.zeros((reference.height, reference.width), dtype=np.uint8) for year in years}

    try:
        for _, glacier in selected.iterrows():
            glacier_id = str(glacier["rgi_id"])
            rgi_geometry = polygonal(glacier.geometry)
            target_geometry = rgi_geometry.buffer(args.buffer_m)
            window = clamp_window(
                from_bounds(*target_geometry.bounds, transform=reference.transform),
                reference.width,
                reference.height,
            )
            if window.width <= 0 or window.height <= 0:
                continue
            transform = window_transform(window, reference.transform)
            shape_hw = (int(window.height), int(window.width))
            rgi_mask = rasterize(
                [(rgi_geometry, 1)],
                out_shape=shape_hw,
                transform=transform,
                fill=0,
                dtype=np.uint8,
                all_touched=False,
            ).astype(bool)
            target_zone = rasterize(
                [(target_geometry, 1)],
                out_shape=shape_hw,
                transform=transform,
                fill=0,
                dtype=np.uint8,
                all_touched=True,
            ).astype(bool)

            evidence: dict[int, dict[str, np.ndarray]] = {}
            clean_masks: list[np.ndarray] = []
            for year in years:
                green, ndsi, ndwi, bsi, evi = (
                    datasets[year]
                    .read(
                        [2, 8, 9, 10, 11],
                        window=window,
                        boundless=False,
                    )
                    .astype(np.float32)
                )
                green = normalize_reflectance(green)
                valid = np.isfinite(green) & np.isfinite(ndsi) & (green > 0)
                clean = valid & (ndsi >= 0.35) & (green >= 0.08)
                clean_masks.append(clean)
                evidence[year] = {
                    "green": green,
                    "ndsi": ndsi,
                    "ndwi": ndwi,
                    "bsi": bsi,
                    "evi": evi,
                    "valid": valid,
                    "clean": clean,
                }
            temporal_clean_fraction = np.mean(np.stack(clean_masks, axis=0), axis=0)

            for year in years:
                annual = evidence[year]
                label_mask, review_mask, score_grid = annual_evidence(
                    ndsi=annual["ndsi"],
                    green=annual["green"],
                    valid=annual["valid"],
                    temporal_clean_fraction=temporal_clean_fraction,
                    rgi_mask=rgi_mask,
                    target_zone=target_zone,
                    pixel_size_m=abs(reference.transform.a),
                )
                label_geometry = mask_to_geometry(label_mask, transform)
                review_geometry = mask_to_geometry(review_mask, transform)
                area_km2 = float(label_mask.sum() * PIXEL_AREA_M2 / 1_000_000)
                rgi_area_km2 = float(rgi_mask.sum() * PIXEL_AREA_M2 / 1_000_000)
                area_delta_percent = 100.0 * (area_km2 - rgi_area_km2) / rgi_area_km2 if rgi_area_km2 else math.nan
                rgi_iou = iou(label_mask, rgi_mask)
                spectral_support = float(annual["clean"][label_mask].mean()) if label_mask.any() else 0.0
                temporal_support = (
                    float((temporal_clean_fraction[label_mask] >= (2 / len(years))).mean()) if label_mask.any() else 0.0
                )
                valid_fraction = float(annual["valid"][target_zone].mean()) if target_zone.any() else 0.0
                review_fraction = float(review_mask.sum() / max(1, np.logical_or(label_mask, review_mask).sum()))
                mean_evidence = float(score_grid[label_mask].mean()) if label_mask.any() else 0.0

                flags: list[str] = []
                if not label_mask.any():
                    flags.append("empty_candidate")
                if rgi_iou < 0.35:
                    flags.append("very_low_rgi_iou")
                elif rgi_iou < 0.55:
                    flags.append("low_rgi_iou")
                if abs(area_delta_percent) > 60:
                    flags.append("very_large_area_delta")
                elif abs(area_delta_percent) > 30:
                    flags.append("large_area_delta")
                if spectral_support < 0.65:
                    flags.append("low_spectral_support")
                if temporal_support < 0.70:
                    flags.append("temporal_disagreement")
                if valid_fraction < 0.95:
                    flags.append("missing_or_invalid_pixels")
                if review_fraction > 0.60:
                    flags.append("large_review_zone")

                quality_score = 100.0 * (
                    0.30 * min(1.0, rgi_iou / 0.70)
                    + 0.30 * spectral_support
                    + 0.20 * temporal_support
                    + 0.10 * valid_fraction
                    + 0.10 * mean_evidence
                )
                confidence = confidence_label(quality_score, flags)
                priority = int(round(min(100.0, 100.0 - quality_score + 20.0 * review_fraction)))
                common = {
                    "glacier_id": glacier_id,
                    "year": year,
                    "area_class": str(glacier.get("area_class", "")),
                    "label_tier": LABEL_TIER,
                    "annotation_status": "provisional_not_gold",
                    "human_review_status": "pending",
                    "confidence": confidence,
                    "quality_score": round(quality_score, 2),
                    "review_priority": priority,
                    "area_km2": round(area_km2, 6),
                    "rgi_area_km2": round(rgi_area_km2, 6),
                    "area_delta_pct": round(area_delta_percent, 2),
                    "rgi_iou": round(rgi_iou, 4),
                    "spectral_support": round(spectral_support, 4),
                    "temporal_support": round(temporal_support, 4),
                    "valid_fraction": round(valid_fraction, 4),
                    "review_fraction": round(review_fraction, 4),
                    "flags": "|".join(flags),
                    "method": "annual_s2_spectral_temporal_rgi_prior_v1",
                }
                label_rows[year].append({**common, "geometry": label_geometry})
                review_rows[year].append(
                    {
                        "glacier_id": glacier_id,
                        "year": year,
                        "review_priority": priority,
                        "reason": "|".join(flags) or "boundary_and_score_ambiguity",
                        "status": "needs_visual_review",
                        "geometry": review_geometry,
                    }
                )
                queue_rows.append(
                    {
                        **{key: value for key, value in common.items() if key != "method"},
                        "source_raster": relative(sources[year]),
                        "label_file": relative(output / f"enhanced_labels_{year}.gpkg"),
                        "claim_eligibility": "training_and_qa_only_not_gold_accuracy",
                    }
                )

                row0, col0 = int(window.row_off), int(window.col_off)
                row1, col1 = row0 + shape_hw[0], col0 + shape_hw[1]
                target = raster_arrays[year][row0:row1, col0:col1]
                target[(review_mask) & (target == 0)] = 2
                target[label_mask] = 1

        for year in years:
            gpkg = output / f"enhanced_labels_{year}.gpkg"
            if gpkg.exists():
                gpkg.unlink()
            labels = gpd.GeoDataFrame(label_rows[year], geometry="geometry", crs=reference.crs)
            reviews = gpd.GeoDataFrame(review_rows[year], geometry="geometry", crs=reference.crs)
            labels.to_file(gpkg, layer="glacier_labels", driver="GPKG")
            reviews.to_file(gpkg, layer="review_zones", driver="GPKG")
            generated.append(gpkg)

            profile = reference.profile.copy()
            profile.update(
                driver="GTiff",
                count=1,
                dtype="uint8",
                nodata=0,
                compress="DEFLATE",
                predictor=2,
                tiled=True,
                blockxsize=256,
                blockysize=256,
            )
            with rasterio.open(raster_paths[year], "w", **profile) as destination:
                destination.write(raster_arrays[year], 1)
                destination.set_band_description(1, "0 background; 1 provisional glacier; 2 review-only")
                destination.update_tags(
                    label_tier=LABEL_TIER,
                    annotation_status="provisional_not_gold",
                    source=relative(sources[year]),
                )
            generated.append(raster_paths[year])
    finally:
        for dataset in datasets.values():
            dataset.close()

    queue_rows.sort(key=lambda row: (-int(row["review_priority"]), int(row["year"]), str(row["glacier_id"])))
    queue_path = output / "enhanced_annotation_queue.csv"
    with queue_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(queue_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(queue_rows)
    generated.append(queue_path)
    qml_styles(output)
    write_qgis_readme(output, years)
    generated.extend([output / "labels.qml", output / "review_zones.qml", output / "README_QGIS.md"])

    source_hashes = {str(year): sha256(path) for year, path in sources.items()}
    old_masks = {
        str(year): sha256(ROOT / f"data/processed/masks/mask_{year}.tif")
        for year in years
        if (ROOT / f"data/processed/masks/mask_{year}.tif").is_file()
    }
    manifest = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label_tier": LABEL_TIER,
        "annotation_status": "provisional_not_gold",
        "purpose": "Strong machine-assisted annotation bootstrap with explicit visual-review zones",
        "method": {
            "annual_source": "Original 11-channel Sentinel-2 stack for each observation year",
            "spectral_evidence": "NDSI and green reflectance",
            "temporal_evidence": f"clean-ice agreement across {years}",
            "spatial_prior": "RGI 7.0 selected cohort, constrained to a 70 m outward search",
            "minimum_component_area_m2": 500,
            "review_layer": "boundary, RGI disagreement, ambiguous evidence and invalid pixels",
        },
        "source_rasters": {
            str(year): {"path": relative(path), "sha256": source_hashes[str(year)]} for year, path in sources.items()
        },
        "excluded_inputs": {
            "annual_processed_masks": {
                "reason": "Excluded from annual evidence because all inspected years have identical SHA-256 digests",
                "sha256_by_year": old_masks,
            }
        },
        "cohort": {
            "glaciers": int(len(selected)),
            "years": years,
            "tasks": len(queue_rows),
            "selection_source": relative(args.bootstrap),
        },
        "outputs": [
            {"path": relative(path), "sha256": sha256(path), "size_bytes": path.stat().st_size} for path in generated
        ],
        "quality_summary": {
            "high_provisional": sum(row["confidence"] == "high_provisional" for row in queue_rows),
            "medium_provisional": sum(row["confidence"] == "medium_provisional" for row in queue_rows),
            "low_provisional": sum(row["confidence"] == "low_provisional" for row in queue_rows),
            "pending_human_review": len(queue_rows),
        },
        "prohibited_claims": [
            "independent expert gold-label accuracy",
            "independent external generalisation",
            "operational hazard probability",
        ],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Created {len(queue_rows)} enhanced provisional tasks for {len(selected)} glaciers "
        f"and {len(years)} years in {output}"
    )
    print(json.dumps(manifest["quality_summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
