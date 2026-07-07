"""Tests for segmentation router — POST /api/predict, GET /api/predict/{task_id}."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

MOCK_SEG_RESULT = {
    "task_id": "abc-123",
    "status": "completed",
    "mask_path": "/tmp/masks/abc-123.png",
    "overlay_path": "/tmp/overlays/abc-123.png",
    "area_km2": 1.23,
}

MOCK_SEG_FAILED = {
    "task_id": "fail-001",
    "status": "failed",
    "error": "Model not found",
}


class TestPredictEndpoint:
    """Tests for POST /api/predict."""

    @patch("app.routers.segmentation.save_upload")
    @patch("app.routers.segmentation.run_segmentation")
    @patch("app.routers.segmentation.save_result")
    @patch("app.routers.segmentation.path_to_url")
    def test_predict_success(self, mock_url, mock_save, mock_seg, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_seg.return_value = MOCK_SEG_RESULT.copy()
        mock_url.side_effect = lambda p: f"/files/{Path(p).name}"

        import asyncio

        from app.routers.segmentation import predict

        file = MagicMock()
        file.filename = "test.tif"
        result = asyncio.run(predict(file=file, model_name="unet", use_tta=True, use_crf=False, ndsi_threshold=None))

        assert result["status"] == "completed"
        assert result["task_id"] == "abc-123"
        mock_seg.assert_called_once()
        mock_save.assert_called_once()

    @patch("app.routers.segmentation.save_upload")
    @patch("app.routers.segmentation.run_segmentation")
    @patch("app.routers.segmentation.save_result")
    def test_predict_failed_no_save(self, mock_save, mock_seg, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_seg.return_value = MOCK_SEG_FAILED.copy()

        import asyncio

        from app.routers.segmentation import predict

        file = MagicMock()
        result = asyncio.run(predict(file=file, model_name="unet", use_tta=False, use_crf=False, ndsi_threshold=None))

        assert result["status"] == "failed"
        mock_save.assert_not_called()

    @patch("app.routers.segmentation.save_upload")
    @patch("app.routers.segmentation.run_segmentation")
    @patch("app.routers.segmentation.save_result")
    @patch("app.routers.segmentation.path_to_url")
    def test_predict_default_model(self, mock_url, mock_save, mock_seg, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_seg.return_value = MOCK_SEG_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.segmentation import predict

        file = MagicMock()
        asyncio.run(predict(file=file, model_name="unet", use_tta=True, use_crf=False, ndsi_threshold=None))

        call_args = mock_seg.call_args
        assert call_args[0][1] == "unet"

    @patch("app.routers.segmentation.save_upload")
    @patch("app.routers.segmentation.run_segmentation")
    @patch("app.routers.segmentation.save_result")
    @patch("app.routers.segmentation.path_to_url")
    def test_predict_ndsi_threshold_passed(self, mock_url, mock_save, mock_seg, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_seg.return_value = MOCK_SEG_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.segmentation import predict

        file = MagicMock()
        asyncio.run(predict(file=file, model_name="ndsi", use_tta=False, use_crf=False, ndsi_threshold=0.4))

        call_args = mock_seg.call_args
        assert call_args[0][4] == 0.4


class TestGetPredictionEndpoint:
    """Tests for GET /api/predict/{task_id}."""

    @patch("app.routers.segmentation.get_result")
    @patch("app.routers.segmentation.path_to_url")
    def test_get_prediction_found(self, mock_url, mock_get):
        mock_get.return_value = {
            "task_id": "abc-123",
            "status": "completed",
            "mask_path": "/tmp/masks/abc-123.png",
            "overlay_path": "/tmp/overlays/abc-123.png",
            "image_path": "/tmp/uploads/img.tif",
        }
        mock_url.side_effect = lambda p: f"/files/{Path(p).name}"

        from app.routers.segmentation import get_prediction

        result = get_prediction(task_id="abc-123")
        assert result["task_id"] == "abc-123"
        assert "/files/" in result["mask_path"]

    @patch("app.routers.segmentation.get_result")
    def test_get_prediction_not_found(self, mock_get):
        mock_get.return_value = None

        from fastapi import HTTPException

        from app.routers.segmentation import get_prediction

        with pytest.raises(HTTPException) as exc_info:
            get_prediction(task_id="nonexistent")
        assert exc_info.value.status_code == 404

    @patch("app.routers.segmentation.get_result")
    @patch("app.routers.segmentation.path_to_url")
    def test_get_prediction_paths_converted(self, mock_url, mock_get):
        mock_get.return_value = {
            "task_id": "abc-123",
            "status": "completed",
            "mask_path": "/tmp/m.png",
            "overlay_path": "/tmp/o.png",
            "image_path": "/tmp/i.tif",
            "thumbnail_path": "/tmp/t.png",
        }
        mock_url.side_effect = lambda p: f"URL({p})"

        from app.routers.segmentation import get_prediction

        result = get_prediction(task_id="abc-123")
        assert result["mask_path"].startswith("URL(")
        assert result["overlay_path"].startswith("URL(")
        assert result["image_path"].startswith("URL(")
        assert result["thumbnail_path"].startswith("URL(")
