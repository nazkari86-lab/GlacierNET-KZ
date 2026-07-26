from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_benchmark_v2_tables.py"
SPEC = importlib.util.spec_from_file_location("build_benchmark_v2_tables", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_benchmark_summary_uses_only_v2_hard_metrics():
    rows = MODULE.build_rows()

    assert len(rows) == 3
    assert all(row["label_quality"] == "silver_rgi_derived" for row in rows)
    assert all(row["hard_dice"] for row in rows)
    assert all(row["boundary_f1"] == "" for row in rows)
    assert all("external_blocked" in row["status"] for row in rows)


def test_sentinel1_compact_ablation_improves_hard_iou_and_area_error():
    rows = {row["experiment"]: row for row in MODULE.build_rows()}
    control = rows["compact_ablation_control_2017_2024"]
    candidate = rows["compact_ablation_sentinel1_2017_2024"]

    assert candidate["hard_iou"] > control["hard_iou"]
    assert abs(candidate["area_error_percent"]) < abs(control["area_error_percent"])
