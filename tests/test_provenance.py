"""Prediction provenance must bind results to exact data, masks, and models."""

from __future__ import annotations

import json

import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.provenance import (
    PREDICTION_PROVENANCE_SCHEMA,
    build_prediction_provenance,
    merge_prediction_provenance,
    sha256_file,
)


def write_raster(path, values, *, count=1):
    array = np.asarray(values, dtype=np.uint8)
    if count == 1:
        array = array[np.newaxis, ...]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=array.shape[2],
        height=array.shape[1],
        count=array.shape[0],
        dtype=array.dtype,
        crs="EPSG:32642",
        transform=from_origin(76.0, 43.0, 10.0, 10.0),
    ) as dataset:
        dataset.write(array)


def test_sha256_file_is_stable(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"glaciernet-kz")
    assert sha256_file(artifact) == "411dd3c1b1d0a85e52f352daa631eb549eca01c946a0bcc3fbaa9599c1568477"


def test_prediction_provenance_binds_source_mask_and_model(tmp_path):
    source = tmp_path / "source.tif"
    predictions = tmp_path / "predictions" / "2024"
    models = tmp_path / "models"
    predictions.mkdir(parents=True)
    models.mkdir()
    write_raster(source, [[1, 2], [3, 4]])
    write_raster(predictions / "ndsi_mask.tif", [[0, 1], [1, 0]])
    write_raster(predictions / "rf_mask.tif", [[1, 1], [0, 0]])
    (models / "random_forest.pkl").write_bytes(b"rf-model")

    record = build_prediction_provenance(
        root=tmp_path,
        year=2024,
        source_path=source,
        prediction_dir=predictions,
        model_names=["ndsi", "rf"],
        ndsi_threshold=0.4,
    )

    assert record["schema"] == PREDICTION_PROVENANCE_SCHEMA
    assert record["source"]["sha256"] == sha256_file(source)
    assert record["models"]["ndsi"]["parameters"] == {"threshold": 0.4}
    assert record["models"]["rf"]["model_sha256"] == sha256_file(models / "random_forest.pkl")
    assert record["models"]["rf"]["mask_sha256"] == sha256_file(predictions / "rf_mask.tif")


def test_merge_prediction_provenance_preserves_compatible_models(tmp_path):
    path = tmp_path / "provenance.json"
    base = {
        "schema": PREDICTION_PROVENANCE_SCHEMA,
        "year": 2024,
        "source": {"sha256": "source"},
        "models": {"ndsi": {"mask_sha256": "a"}},
    }
    merge_prediction_provenance(path, base)
    updated = {
        **base,
        "models": {"rf": {"mask_sha256": "b"}},
    }

    merged = merge_prediction_provenance(path, updated)

    assert set(merged["models"]) == {"ndsi", "rf"}
    assert json.loads(path.read_text(encoding="utf-8")) == merged
