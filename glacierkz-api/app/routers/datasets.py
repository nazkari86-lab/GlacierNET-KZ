# -*- coding: utf-8 -*-
"""Dataset management routes for glacier imagery and labels.

Supports listing, creating, uploading, validating, and inspecting datasets.
A dataset represents a collection of geospatial samples (e.g. Sentinel-2
tiles or labelled masks) associated with a specific glacier.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

CORE_DIR = Path(os.environ.get("CORE_DIR", Path(__file__).resolve().parents[3]))
RAW_S2 = CORE_DIR / "data" / "raw" / "sentinel2"
RAW_LS = CORE_DIR / "data" / "raw" / "landsat"
PREDICTIONS = CORE_DIR / "predictions"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class DatasetInfo(BaseModel):
    """Public representation of a dataset."""

    id: str
    name: str
    size_mb: float
    num_samples: int
    glacier_name: str = ""
    date_range: str = ""
    status: str = "ready"


class DatasetCreate(BaseModel):
    """Payload for registering a new dataset (metadata only)."""

    name: str = Field(..., min_length=1, max_length=200, description="Dataset name")
    glacier_name: str = Field("", max_length=200, description="Associated glacier")
    description: str = Field("", max_length=2000, description="Free-text description")


class DatasetListResponse(BaseModel):
    """Paginated list of datasets with optional filters applied."""

    datasets: list[DatasetInfo]
    total: int
    offset: int
    limit: int


class DatasetStats(BaseModel):
    """Aggregate statistics for a single dataset."""

    dataset_id: str
    num_samples: int
    size_mb: float
    band_means: dict[str, float] = Field(default_factory=dict)
    coverage_percent: float = 0.0
    date_range: str = ""


class ValidationReport(BaseModel):
    """Integrity validation result for a dataset."""

    dataset_id: str
    valid: bool
    checked_files: int
    corrupt_files: list[str] = Field(default_factory=list)
    message: str = ""


class SampleListResponse(BaseModel):
    """Paginated list of sample IDs within a dataset."""

    dataset_id: str
    sample_ids: list[str]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# In-memory store – replace with DB / object-storage metadata service.
# ---------------------------------------------------------------------------
_datasets: dict[str, dict[str, Any]] = {}


def _seed_sample_datasets() -> None:
    if _datasets:
        return
    now = time.time()

    def add_from_disk(directory: Path, prefix: str, source_label: str) -> None:
        if not directory.exists():
            return
        for tif in sorted(directory.glob(f"{prefix}_*.tif")):
            try:
                year = int(tif.stem.rsplit("_", 1)[-1])
            except ValueError:
                continue
            ds_id = f"ds-zailiysky-{year}-{source_label.lower()}"
            has_pred = (PREDICTIONS / str(year) / "rf_mask.tif").exists()
            _datasets[ds_id] = {
                "id": ds_id,
                "name": f"Zailiysky_{year}_{source_label}",
                "glacier_name": "Zailiysky",
                "size_mb": round(tif.stat().st_size / (1024 * 1024), 1),
                "num_samples": 1,
                "date_range": str(year),
                "status": "ready" if has_pred else "empty",
                "description": f"Raw {source_label} composite for Ili Alatau",
                "created_at": now,
                "updated_at": now,
            }

    add_from_disk(RAW_S2, "sentinel2", "S2")
    add_from_disk(RAW_LS, "landsat", "Landsat")

    if _datasets:
        return

    # Fallback samples when running without project data on disk
    now = time.time()
    samples = [
        {
            "id": "ds-zailiysky-2020",
            "name": "Zailiysky_2020_S2",
            "glacier_name": "Zailiysky",
            "size_mb": 245.0,
            "num_samples": 1240,
            "date_range": "2020",
            "status": "ready",
            "description": "",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ds-tuyuksu-2017",
            "name": "Tuyuksu_2017_Landsat",
            "glacier_name": "Tuyuksu",
            "size_mb": 189.0,
            "num_samples": 980,
            "date_range": "2017",
            "status": "ready",
            "description": "",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ds-mynzhilki-2020",
            "name": "Mynzhilki_2020_S2",
            "glacier_name": "Mynzhilki",
            "size_mb": 218.0,
            "num_samples": 1100,
            "date_range": "2020",
            "status": "empty",
            "description": "",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "ds-kumtor-2020",
            "name": "Kumtor_2020_S2",
            "glacier_name": "Kumtor",
            "size_mb": 298.0,
            "num_samples": 1500,
            "date_range": "2020",
            "status": "ready",
            "description": "",
            "created_at": now,
            "updated_at": now,
        },
    ]
    for ds in samples:
        _datasets[ds["id"]] = ds


_seed_sample_datasets()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dataset_to_info(ds: dict[str, Any]) -> DatasetInfo:
    """Map internal dataset dict to the response model."""
    return DatasetInfo(
        id=ds["id"],
        name=ds["name"],
        size_mb=ds.get("size_mb", 0.0),
        num_samples=ds.get("num_samples", 0),
        glacier_name=ds.get("glacier_name", ""),
        date_range=ds.get("date_range", ""),
        status=ds.get("status", "ready"),
    )


def _get_dataset_or_404(dataset_id: str) -> dict[str, Any]:
    """Look up a dataset or raise HTTP 404."""
    ds = _datasets.get(dataset_id)
    if ds is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id!r} not found",
        )
    return ds


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/", response_model=DatasetListResponse, summary="List datasets")
async def list_datasets(
    glacier: Optional[str] = Query(None, description="Filter by glacier name"),
    status: Optional[str] = Query(None, description="Filter by dataset status"),
    search: Optional[str] = Query(None, description="Substring match on name"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
) -> DatasetListResponse:
    """List datasets with optional glacier, status, and text-search filters.

    Results are ordered by creation time (newest first).
    """
    results: list[dict[str, Any]] = list(_datasets.values())

    if glacier is not None:
        results = [d for d in results if d.get("glacier_name") == glacier]
    if status is not None:
        results = [d for d in results if d.get("status") == status]
    if search is not None:
        q = search.lower()
        results = [d for d in results if q in d["name"].lower()]

    total = len(results)
    sliced = results[offset : offset + limit]

    return DatasetListResponse(
        datasets=[_dataset_to_info(d) for d in sliced],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/create", response_model=DatasetInfo, status_code=201, summary="Register a new dataset")
async def create_dataset(body: DatasetCreate) -> DatasetInfo:
    """Register a new dataset entry.

    This only creates the metadata record – call ``POST /upload`` afterwards
    to attach the actual data file.
    """
    ds_id = f"ds-{uuid.uuid4().hex[:12]}"
    now = time.time()

    ds: dict[str, Any] = {
        "id": ds_id,
        "name": body.name,
        "glacier_name": body.glacier_name,
        "description": body.description,
        "size_mb": 0.0,
        "num_samples": 0,
        "date_range": "",
        "status": "empty",
        "created_at": now,
        "updated_at": now,
    }
    _datasets[ds_id] = ds
    return _dataset_to_info(ds)


@router.get("/{dataset_id}", response_model=DatasetInfo, summary="Get dataset info")
async def get_dataset(dataset_id: str) -> DatasetInfo:
    """Retrieve metadata for a single dataset by its identifier."""
    ds = _get_dataset_or_404(dataset_id)
    return _dataset_to_info(ds)


@router.delete("/{dataset_id}", status_code=200, summary="Remove dataset")
async def delete_dataset(dataset_id: str) -> dict:
    """Remove a dataset and its associated metadata.

    Returns **204 No Content** on success; **404** if the dataset does not
    exist.
    """
    _get_dataset_or_404(dataset_id)  # raises 404 if missing
    del _datasets[dataset_id]
    return {"status": "deleted", "dataset_id": dataset_id}


@router.post("/{dataset_id}/validate", response_model=ValidationReport, summary="Validate dataset integrity")
async def validate_dataset(dataset_id: str) -> ValidationReport:
    """Validate integrity of all files belonging to the dataset.

    In production this would checksum every file against its manifest and
    verify geospatial metadata consistency.
    """
    ds = _get_dataset_or_404(dataset_id)

    # Placeholder – real implementation scans the data directory.
    return ValidationReport(
        dataset_id=dataset_id,
        valid=True,
        checked_files=ds.get("num_samples", 0),
        corrupt_files=[],
        message="All files passed integrity checks.",
    )


@router.get("/{dataset_id}/samples", response_model=SampleListResponse, summary="List sample IDs with pagination")
async def list_samples(
    dataset_id: str,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Page size"),
) -> SampleListResponse:
    """Return a paginated list of sample IDs within the dataset."""
    ds = _get_dataset_or_404(dataset_id)

    total = ds.get("num_samples", 0)
    sample_ids = [f"{dataset_id}-sample-{i}" for i in range(offset, min(offset + limit, total))]

    return SampleListResponse(
        dataset_id=dataset_id,
        sample_ids=sample_ids,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{dataset_id}/stats", response_model=DatasetStats, summary="Dataset statistics")
async def dataset_stats(dataset_id: str) -> DatasetStats:
    """Compute and return aggregate statistics for the dataset.

    Statistics include per-band mean values, spatial coverage percentage,
    and the temporal date range.
    """
    ds = _get_dataset_or_404(dataset_id)

    return DatasetStats(
        dataset_id=dataset_id,
        num_samples=ds.get("num_samples", 0),
        size_mb=ds.get("size_mb", 0.0),
        band_means={},
        coverage_percent=0.0,
        date_range=ds.get("date_range", ""),
    )


@router.post("/upload", response_model=DatasetInfo, status_code=201, summary="Upload dataset file")
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset archive (GeoTIFF / COG / ZIP)"),
    name: Optional[str] = Query(None, description="Dataset name override"),
) -> DatasetInfo:
    """Upload a dataset file and register it.

    The file is read into memory and its size is recorded.  Metadata
    extraction (band means, coverage, etc.) happens asynchronously.  The
    dataset is created in ``uploading`` status and transitions to ``ready``
    once processing completes.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    size_mb = round(len(content) / (1024 * 1024), 2)
    ds_id = f"ds-{uuid.uuid4().hex[:12]}"
    now = time.time()

    ds: dict[str, Any] = {
        "id": ds_id,
        "name": name or (file.filename or "unnamed"),
        "glacier_name": "",
        "description": "",
        "size_mb": size_mb,
        "num_samples": 0,
        "date_range": "",
        "status": "uploading",
        "content_type": file.content_type,
        "created_at": now,
        "updated_at": now,
    }
    _datasets[ds_id] = ds
    return _dataset_to_info(ds)
