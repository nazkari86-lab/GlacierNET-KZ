"""Reproducible evidence packages used by charts, exports and the LLM.

The service deliberately reads the release tables instead of asking an LLM to
infer numbers from prose.  It is small and dependency-light so the same values
can be inspected in the UI, exported, and passed to Groq.
"""

import csv
import math
from pathlib import Path

import numpy as np

from app.utils import resolve_core_dir

CORE_DIR = resolve_core_dir(__file__)
TABLES_DIR = CORE_DIR / "results" / "tables"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required evidence table is missing: {path.relative_to(CORE_DIR)}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _point(row: dict[str, str]) -> dict:
    return {
        "year": int(row["year"]),
        "area_km2": round(float(row["area_km2"]), 2),
        "sensor": row["sensor"],
        "quality_score": int(float(row["quality_score"])),
        "confidence": row["confidence"],
        "included_in_exploratory_trend": row["include_in_strict_trend"].strip().lower() == "true",
        "caveat": row["caveat"],
    }


def _linear_summary(points: list[dict]) -> dict | None:
    if len(points) < 3:
        return None
    x = np.asarray([point["year"] for point in points], dtype=float)
    y = np.asarray([point["area_km2"] for point in points], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residuals = y - fitted
    sse = float(np.sum(residuals**2))
    centered = float(np.sum((x - x.mean()) ** 2))
    stderr = math.sqrt(sse / (len(x) - 2) / centered) if centered > 0 and len(x) > 2 else 0.0
    # Normal 95% interval is explicitly labelled approximate; without a
    # glacier-level paired validation set it must not be presented as a CI for
    # true glacier change.
    margin = 1.96 * stderr
    ss_total = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - sse / ss_total if ss_total else 0.0
    return {
        "n_observations": len(points),
        "first_year": int(x.min()),
        "last_year": int(x.max()),
        "slope_km2_per_year": round(float(slope), 3),
        "slope_interval_95_approx": [round(float(slope - margin), 3), round(float(slope + margin), 3)],
        "r_squared": round(float(r_squared), 3),
        "net_change_km2": round(float(y[-1] - y[0]), 2),
        "net_change_percent": round(float((y[-1] - y[0]) / y[0] * 100), 2) if y[0] else None,
    }


def get_trend_evidence() -> dict:
    """Build a chart-ready, source-bound trend package from local release data."""
    rows = _read_csv(TABLES_DIR / "decision_ready_area_timeseries.csv")
    points = sorted((_point(row) for row in rows), key=lambda point: point["year"])
    exploratory = [point for point in points if point["included_in_exploratory_trend"]]

    anomalies = []
    for row in _read_csv(TABLES_DIR / "temporal_anomalies.csv"):
        if row.get("status") not in {"baseline", "accepted"}:
            anomalies.append(
                {
                    "year": int(row["year"]),
                    "status": row["status"],
                    "relative_change_percent": round(float(row["relative_change"]) * 100, 1),
                    "reason": row["reason"],
                }
            )

    return {
        "title": "GlacierNET-KZ local area evidence",
        "status": "exploratory_not_adjudicated",
        "primary_table": "results/tables/decision_ready_area_timeseries.csv",
        "points": points,
        "exploratory_points": exploratory,
        "exploratory_linear_trend": _linear_summary(exploratory),
        "flagged_temporal_anomalies": anomalies,
        "limitations": [
            "Area is a project-level segmentation output, not measured glacier volume or water availability.",
            "The time series mixes sensors outside the exploratory Sentinel-2 subset; do not compare those values as one calibrated scientific trend.",
            "The 95% interval describes fitted-line sampling uncertainty only. It is not a glacier-level validation confidence interval.",
            "No climate-station, temperature, precipitation, population, or infrastructure claim is included in this evidence package.",
            "Several included observations retain scene-quality and temporal-change caveats; inspect the point tooltip before using a value.",
        ],
    }


def trend_evidence_prompt(evidence: dict) -> str:
    """Compact, unambiguous contract for the language model."""
    summary = evidence.get("exploratory_linear_trend") or {}
    return (
        "VERIFIED LOCAL EVIDENCE (authoritative):\n"
        f"source={evidence['primary_table']}; status={evidence['status']}; "
        f"exploratory_trend={summary}; anomalies={evidence['flagged_temporal_anomalies']}; "
        f"limitations={evidence['limitations']}\n\n"
        "RULES: Use only numeric facts in VERIFIED LOCAL EVIDENCE or the supplied project context. "
        "Do not invent climate observations, causes, stations, forecasts, graphs, or validation metrics. "
        "Call the trend exploratory, name the source table, and end with the listed limitations."
    )
