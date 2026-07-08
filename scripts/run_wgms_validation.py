#!/usr/bin/env python3
"""Run WGMS validation for Tuyuksu glacier against FoG reference data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config, metrics

WGMS_JSON = config.PROJECT_ROOT / "data" / "wgms" / "tuyuksu_areas.json"
FOG_STATE = config.PROJECT_ROOT / "data" / "wgms" / "raw" / "fog_extracted" / "data" / "state.csv"
OUTPUT = config.TABLES_DIR / "wgms_validation_tuyuksu.csv"
REPORT = config.RESULTS_DIR / "wgms_validation_report.json"


def refresh_wgms_from_fog() -> dict[int, float]:
    """Re-parse FoG state.csv if available."""
    if not FOG_STATE.exists():
        if WGMS_JSON.exists():
            return {int(k): float(v) for k, v in json.loads(WGMS_JSON.read_text()).items()}
        raise FileNotFoundError("No WGMS data found. Run scripts/wgms_setup.py first.")

    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "wgms_setup.py"), "--fog-csv", str(FOG_STATE)],
        check=True,
    )
    return {int(k): float(v) for k, v in json.loads(WGMS_JSON.read_text()).items()}


def load_predicted_tuyuksu_areas() -> dict[int, float]:
    """Load U-Net predicted areas for overlap years (bbox-level proxy until sub-glacier crop)."""
    areas_path = config.TABLES_DIR / "glacier_areas_all_years.csv"
    if not areas_path.exists():
        return {}

    import pandas as pd

    df = pd.read_csv(areas_path)
    unet = df[df["method"].str.contains("U-Net|unet", case=False, na=False)]
    if unet.empty:
        unet = df[df["method"] == "RF"]

    result: dict[int, float] = {}
    for _, row in unet.iterrows():
        year = int(row["year"])
        area = float(row["area_km2"])
        # Scale bbox area to Tuyuksu proportion (~2.2 km² / ~450 km² ≈ 0.005)
        # For validation we use relative trend; absolute RMSE requires glacier crop.
        tuyuksu_scale = 2.2 / 450.0
        result[year] = round(area * tuyuksu_scale, 4)
    return result


def main() -> None:
    print("Refreshing WGMS FoG data for Tuyuksu (glacier_id=817)...")
    wgms_areas = refresh_wgms_from_fog()
    print(f"  WGMS: {len(wgms_areas)} years ({min(wgms_areas)}–{max(wgms_areas)})")

    predicted = load_predicted_tuyuksu_areas()
    if not predicted:
        print("WARNING: No predicted areas found in glacier_areas_all_years.csv")
        print("  WGMS data ready for notebook 05 — run temporal analysis first.")
        return

    common = sorted(set(predicted) & set(wgms_areas))
    if len(common) < 2:
        print(f"Only {len(common)} overlapping years — need sub-glacier crop for accurate RMSE.")
        print("  WGMS years available:", sorted(wgms_areas.keys())[-10:])
        print("  Predicted years:", sorted(predicted.keys()))
        return

    rmse, years, diffs = metrics.rmse_against_wgms(predicted, wgms_areas)
    mae = sum(abs(d) for d in diffs.values()) / len(diffs)

    print(f"\nWGMS Validation (scaled bbox proxy, {len(years)} years: {years[0]}–{years[-1]})")
    print(f"  RMSE: {rmse:.4f} km²")
    print(f"  MAE:  {mae:.4f} km²")
    print(f"  Note: For publication-grade RMSE, crop masks to RGI Tuyuksu polygon.")

    config.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    import csv

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "predicted_km2", "wgms_km2", "diff_km2"])
        for y in years:
            writer.writerow([y, predicted[y], wgms_areas[y], diffs[y]])

    report = {
        "glacier": "Tuyuksu (WGMS ID 817)",
        "rmse_km2": round(rmse, 4),
        "mae_km2": round(mae, 4),
        "n_years": len(years),
        "years": years,
        "method": "scaled_bbox_proxy",
        "note": "Crop to RGI RGI2000-v7.0-G-13-33843 for publication-grade RMSE",
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved → {OUTPUT}")
    print(f"Saved → {REPORT}")


if __name__ == "__main__":
    main()
