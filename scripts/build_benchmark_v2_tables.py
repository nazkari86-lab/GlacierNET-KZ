#!/usr/bin/env python3
"""Build the publishable Benchmark v2 summary from validated evaluation reports."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "benchmarks/v2/tables/metrics_summary.csv"
REPORTS = (
    (
        "temporal_s2_terrain_2016_2024",
        "U-Net S2+terrain",
        ROOT / "results/temporal_benchmark_unet_sentinel2_terrain_2016_2024.json",
    ),
    (
        "compact_ablation_control_2017_2024",
        "U-Net S2+terrain compact control",
        ROOT / "results/ablation_unet_sentinel2_terrain_control_2017_2024.json",
    ),
    (
        "compact_ablation_sentinel1_2017_2024",
        "U-Net S2+terrain+S1 VV/VH",
        ROOT / "results/ablation_unet_sentinel2_terrain_s1_2017_2024.json",
    ),
)
FIELDS = (
    "experiment",
    "model",
    "label_quality",
    "region_scope",
    "threshold",
    "hard_dice",
    "hard_dice_ci_lower",
    "hard_dice_ci_upper",
    "hard_iou",
    "precision",
    "recall",
    "boundary_f1",
    "hausdorff95_m",
    "assd_m",
    "area_error_km2",
    "area_error_percent",
    "n_glaciers",
    "status",
)


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for experiment, model, path in REPORTS:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("benchmark_protocol_version") != "2.0":
            raise ValueError(f"{path.name} is not a Benchmark v2 report")
        hard = report.get("hard_metrics")
        if not isinstance(hard, dict):
            raise ValueError(f"{path.name} has no validation-calibrated hard_metrics")
        if report.get("label_quality_tier") != "silver":
            raise ValueError(f"{path.name} must remain labelled silver")
        rows.append(
            {
                "experiment": experiment,
                "model": model,
                "label_quality": "silver_rgi_derived",
                "region_scope": "Ile_Alatau_one_AOI_temporal_test_2024",
                "threshold": hard["threshold"],
                "hard_dice": hard["hard_dice"],
                "hard_dice_ci_lower": "",
                "hard_dice_ci_upper": "",
                "hard_iou": hard["hard_iou"],
                "precision": hard["precision"],
                "recall": hard["recall"],
                "boundary_f1": "",
                "hausdorff95_m": "",
                "assd_m": "",
                "area_error_km2": hard["area_error_km2"],
                "area_error_percent": hard["area_error_percent"],
                "n_glaciers": "",
                "status": "complete_one_aoi_silver; glacier_CI_boundary_external_blocked",
            }
        )
    return rows


def main() -> int:
    rows = build_rows()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} verified silver rows to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
