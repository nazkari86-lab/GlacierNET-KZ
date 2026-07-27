from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.services.glacier_registry_service import list_glaciers
from app.routers.years import map_layer_image, map_layer_metadata

pytestmark = pytest.mark.local_data


def test_bulk_registry_geometry_is_explicitly_opt_in() -> None:
    compact = list_glaciers(limit=1)
    spatial = list_glaciers(limit=1, include_geometry=True)

    assert compact["total"] == spatial["total"]
    assert "geometry" not in compact["glaciers"][0]
    assert spatial["glaciers"][0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert spatial["glaciers"][0]["geometry"]["coordinates"]


def test_year_map_layer_is_georeferenced_and_renderable() -> None:
    metadata = map_layer_metadata(2024)
    image = map_layer_image(2024)

    assert metadata["year"] == 2024
    assert metadata["method"] in {"ndsi", "rf", "unet"}
    assert metadata["bounds"][0][0] < metadata["bounds"][1][0]
    assert metadata["bounds"][0][1] < metadata["bounds"][1][1]
    assert metadata["image_url"].endswith("/2024/map-layer.png")
    assert image.media_type == "image/png"
    assert image.body.startswith(b"\x89PNG\r\n\x1a\n")
