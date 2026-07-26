#!/usr/bin/env python3
"""Flag physically suspicious annual glacier-area changes."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.temporal_quality import classify_annual_change  # noqa: E402

DEFAULT_AREAS = ROOT / "results/tables/glacier_areas_all_years.csv"
DEFAULT_QUALITY = ROOT / "results/tables/year_quality_scores.csv"
DEFAULT_OUTPUT = ROOT / "results/tables/temporal_anomalies.csv"

FIELDS = [
    "year",
    "area_km2",
    "previous_area_km2",
    "relative_change",
    "z_score",
    "snow_fraction",
    "cloud_fraction",
    "status",
    "reason",
]


classify_change = classify_annual_change


def _optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    parsed = float(value)
    return parsed if math.isfinite(parsed) else None


def build_temporal_rows(
    area_rows: list[dict[str, str]],
    quality_rows: list[dict[str, str]],
    *,
    sensor: str,
    method: str,
) -> list[dict[str, str | int | float]]:
    quality = {int(row["year"]): row for row in quality_rows}
    selected = sorted(
        (
            (int(row["year"]), float(row["area_km2"]))
            for row in area_rows
            if row.get("sensor") == sensor
            and row.get("method") == method
            and quality.get(int(row["year"]), {}).get("source_flag") != "sentinel2_toa_fallback"
        ),
        key=lambda item: item[0],
    )
    if len(selected) < 2:
        raise ValueError(f"need at least two comparable {sensor}/{method} annual areas")

    changes = np_array(
        [abs(area - previous_area) / previous_area for (_, previous_area), (_, area) in zip(selected, selected[1:])],
    )
    median = float(sorted(changes)[len(changes) // 2])
    deviations = [abs(value - median) for value in changes]
    mad = float(sorted(deviations)[len(deviations) // 2])

    output: list[dict[str, str | int | float]] = []
    previous_area: float | None = None
    for year, area in selected:
        relative_change = None if previous_area is None else abs(area - previous_area) / previous_area
        status, reason = classify_change(relative_change)
        z_score = 0.0
        if relative_change is not None and mad > 0:
            z_score = 0.67448975 * (relative_change - median) / mad
        quality_row = quality.get(year, {})
        snow = _optional_float(quality_row.get("snow_fraction"))
        cloud = _optional_float(quality_row.get("cloud_fraction"))
        missing_signals = [
            name for name, value in (("snow_fraction", snow), ("cloud_fraction", cloud)) if value is None
        ]
        if missing_signals:
            reason += "; missing acquisition QA: " + ", ".join(missing_signals)
        output.append(
            {
                "year": year,
                "area_km2": area,
                "previous_area_km2": "" if previous_area is None else previous_area,
                "relative_change": "" if relative_change is None else relative_change,
                "z_score": z_score,
                "snow_fraction": "" if snow is None else snow,
                "cloud_fraction": "" if cloud is None else cloud,
                "status": status,
                "reason": reason,
            }
        )
        previous_area = area
    return output


def np_array(values: list[float]) -> list[float]:
    """Small explicit helper kept dependency-free for this CLI."""
    return [float(value) for value in values]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--areas", type=Path, default=DEFAULT_AREAS)
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sensor", default="Sentinel-2")
    parser.add_argument("--method", default="RF")
    parser.add_argument("--fail-on-reject", action="store_true")
    args = parser.parse_args()

    rows = build_temporal_rows(
        read_csv(args.areas),
        read_csv(args.quality),
        sensor=args.sensor,
        method=args.method,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    rejects = [row for row in rows if row["status"] == "reject"]
    print(f"Wrote {len(rows)} rows to {args.output}; rejected years: {[row['year'] for row in rejects]}")
    return 1 if args.fail_on_reject and rejects else 0


if __name__ == "__main__":
    raise SystemExit(main())
