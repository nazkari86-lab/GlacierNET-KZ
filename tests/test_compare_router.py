"""Tests for compare router — POST /api/compare."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

MOCK_COMPARE_RESULT = {
    "task_id": "cmp-001",
    "segments": [
        {"model_name": "unet", "mask_path": "/tmp/m/unet.png", "overlay_path": "/tmp/o/unet.png", "area_km2": 1.1},
        {"model_name": "ndsi", "mask_path": "/tmp/m/ndsi.png", "overlay_path": "/tmp/o/ndsi.png", "area_km2": 1.3},
    ],
}


class TestCompareEndpoint:
    """Tests for POST /api/compare."""

    @patch("app.routers.compare.save_upload")
    @patch("app.routers.compare.run_compare")
    @patch("app.routers.compare.path_to_url")
    def test_compare_success(self, mock_url, mock_compare, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_compare.return_value = MOCK_COMPARE_RESULT.copy()
        mock_url.side_effect = lambda p: f"/files/{Path(p).name}"

        import asyncio

        from app.routers.compare import compare_models

        file = MagicMock()
        result = asyncio.run(compare_models(file=file, model_names="unet,ndsi", use_tta=True, use_crf=False))

        assert result["task_id"] == "cmp-001"
        assert len(result["segments"]) == 2
        assert mock_compare.called

    @patch("app.routers.compare.save_upload")
    @patch("app.routers.compare.run_compare")
    @patch("app.routers.compare.path_to_url")
    def test_compare_default_models(self, mock_url, mock_compare, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_compare.return_value = MOCK_COMPARE_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.compare import compare_models

        file = MagicMock()
        asyncio.run(compare_models(file=file, model_names="unet,attention_unet,ndsi,ensemble", use_tta=True, use_crf=False))

        call_args = mock_compare.call_args
        assert call_args[0][1] == ["unet", "attention_unet", "ndsi", "ensemble"]

    @patch("app.routers.compare.save_upload")
    @patch("app.routers.compare.run_compare")
    @patch("app.routers.compare.path_to_url")
    def test_compare_model_names_stripped(self, mock_url, mock_compare, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_compare.return_value = MOCK_COMPARE_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.compare import compare_models

        file = MagicMock()
        asyncio.run(compare_models(file=file, model_names=" unet , ndsi ", use_tta=False, use_crf=False))

        call_args = mock_compare.call_args
        assert call_args[0][1] == ["unet", "ndsi"]

    @patch("app.routers.compare.save_upload")
    @patch("app.routers.compare.run_compare")
    @patch("app.routers.compare.path_to_url")
    def test_compare_mask_paths_converted(self, mock_url, mock_compare, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_compare.return_value = MOCK_COMPARE_RESULT.copy()
        mock_url.side_effect = lambda p: f"URL({p})"

        import asyncio

        from app.routers.compare import compare_models

        file = MagicMock()
        result = asyncio.run(compare_models(file=file, model_names="unet", use_tta=False, use_crf=False))

        for seg in result["segments"]:
            assert seg["mask_path"].startswith("URL(")
            assert seg["overlay_path"].startswith("URL(")
