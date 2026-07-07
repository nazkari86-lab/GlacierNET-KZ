"""Tests for datasets router — CRUD, create, validate, samples, stats."""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

from app.routers.datasets import (
    DatasetCreate,
    _datasets,
    create_dataset,
    dataset_stats,
    delete_dataset,
    get_dataset,
    list_datasets,
    list_samples,
    validate_dataset,
)


@pytest.fixture(autouse=True)
def clear_datasets():
    """Clear in-memory dataset store between tests."""
    _datasets.clear()
    yield
    _datasets.clear()


def _seed_dataset(ds_id: str, name: str = "Test DS", glacier: str = "Aksau", status: str = "ready"):
    _datasets[ds_id] = {
        "id": ds_id,
        "name": name,
        "glacier_name": glacier,
        "date_range": "2020-01-01/2020-12-31",
        "size_mb": 512.0,
        "num_samples": 1000,
        "status": status,
        "created_at": 1700000000.0,
    }


def _seed_datasets(n: int, glacier: str = "Aksau", status: str = "ready"):
    for i in range(n):
        _seed_dataset(f"ds-{i:03d}", name=f"Dataset {i}", glacier=glacier, status=status)


class TestListDatasets:
    def test_empty(self):
        result = asyncio.run(list_datasets(glacier=None, status=None, search=None, offset=0, limit=20))
        assert result.total == 0
        assert result.datasets == []

    def test_returns_all(self):
        _seed_datasets(5)
        result = asyncio.run(list_datasets(glacier=None, status=None, search=None, offset=0, limit=20))
        assert result.total == 5
        assert len(result.datasets) == 5

    def test_filter_by_glacier(self):
        _seed_datasets(3, glacier="Aksau")
        _seed_datasets(2, glacier="Shevalier")
        result = asyncio.run(list_datasets(glacier="Shevalier", status=None, search=None, offset=0, limit=20))
        assert result.total == 2

    def test_filter_by_status(self):
        _seed_datasets(3, status="ready")
        _seed_datasets(2, status="processing")
        result = asyncio.run(list_datasets(glacier=None, status="processing", search=None, offset=0, limit=20))
        assert result.total == 2

    def test_pagination(self):
        _seed_datasets(10)
        result = asyncio.run(list_datasets(glacier=None, status=None, search=None, limit=4, offset=2))
        assert len(result.datasets) == 4


class TestCreateDataset:
    def test_create(self):
        body = DatasetCreate(name="New Dataset", glacier_name="Tuyuksu")
        result = asyncio.run(create_dataset(body=body))
        assert result.name == "New Dataset"
        assert result.id in _datasets

    def test_create_default_status(self):
        body = DatasetCreate(name="Empty")
        result = asyncio.run(create_dataset(body=body))
        assert result.status == "empty"


class TestGetDataset:
    def test_found(self):
        _seed_dataset("ds-001")
        result = asyncio.run(get_dataset(dataset_id="ds-001"))
        assert result.id == "ds-001"

    def test_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_dataset(dataset_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestDeleteDataset:
    def test_delete_success(self):
        _seed_dataset("ds-001")
        asyncio.run(delete_dataset(dataset_id="ds-001"))
        assert "ds-001" not in _datasets

    def test_delete_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(delete_dataset(dataset_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestValidateDataset:
    def test_valid_dataset(self):
        _seed_dataset("ds-001")
        result = asyncio.run(validate_dataset(dataset_id="ds-001"))
        assert result.valid is True
        assert result.checked_files == 1000
        assert result.corrupt_files == []

    def test_validate_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(validate_dataset(dataset_id="nonexistent"))
        assert exc_info.value.status_code == 404


class TestListSamples:
    def test_returns_samples(self):
        _seed_dataset("ds-001")
        result = asyncio.run(list_samples(dataset_id="ds-001", offset=0, limit=50))
        assert result.total == 1000
        assert len(result.sample_ids) == 50  # default limit

    def test_samples_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(list_samples(dataset_id="nonexistent", offset=0, limit=50))
        assert exc_info.value.status_code == 404


class TestDatasetStats:
    def test_returns_stats(self):
        _seed_dataset("ds-001")
        result = asyncio.run(dataset_stats(dataset_id="ds-001"))
        assert result.num_samples == 1000
        assert result.size_mb == 512.0

    def test_stats_not_found(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(dataset_stats(dataset_id="nonexistent"))
        assert exc_info.value.status_code == 404
