"""Measured summaries from the expert-validated HMA lake-terminating dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

CENTRAL_ASIA_MOUNTAINS = (
    "Northern/Western Tien Shan",
    "Central Tien Shan",
    "Dzhungarsky Alatau",
)


def build_hma_reference_metrics(gpkg_path: str | Path) -> dict[str, Any]:
    """Aggregate publisher geometries without inventing record-level matches."""
    import geopandas as gpd

    path = Path(gpkg_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    glacier_1990 = gpd.read_file(path, layer="glacier_1990")
    glacier_2022 = gpd.read_file(path, layer="glaicer_2022")
    lake_1990 = gpd.read_file(path, layer="lake_1990")
    lake_2022 = gpd.read_file(path, layer="lake_2022")

    def select(frame):
        return frame[frame["Mountain"].isin(CENTRAL_ASIA_MOUNTAINS)]

    glacier_1990 = select(glacier_1990)
    glacier_2022 = select(glacier_2022)
    lake_1990 = select(lake_1990)
    lake_2022 = select(lake_2022)
    glacier_area_1990 = float(glacier_1990["Area"].sum())
    glacier_area_2022 = float(glacier_2022["Area"].sum())
    lake_area_1990 = float(lake_1990["Area"].sum())
    lake_area_2022 = float(lake_2022["Area"].sum())
    return {
        "status": "measured_reference",
        "mountain_systems": list(CENTRAL_ASIA_MOUNTAINS),
        "glacier_records_1990": int(len(glacier_1990)),
        "glacier_records_2022": int(len(glacier_2022)),
        "glacier_area_1990_km2": glacier_area_1990,
        "glacier_area_2022_km2": glacier_area_2022,
        "aggregate_glacier_area_change_percent": (glacier_area_2022 / glacier_area_1990 - 1.0) * 100.0,
        "lake_records_1990": int(len(lake_1990)),
        "lake_records_2022": int(len(lake_2022)),
        "lake_area_1990_km2": lake_area_1990,
        "lake_area_2022_km2": lake_area_2022,
        "aggregate_lake_area_change_percent": (lake_area_2022 / lake_area_1990 - 1.0) * 100.0,
        "pairing_note": (
            "Aggregate publisher-layer comparison. Record identifiers are not assumed one-to-one "
            "because the source contains split/merged glacier and lake objects."
        ),
    }
