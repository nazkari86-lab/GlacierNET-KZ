"""Tests for uncertainty router — POST /api/uncertainty."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))

MOCK_UNCERTAINTY_RESULT = {
    "task_id": "unc-001",
    "mean_path": "/tmp/unc/mean.png",
    "std_path": "/tmp/unc/std.png",
    "entropy_path": "/tmp/unc/entropy.png",
}


class TestUncertaintyEndpoint:
    """Tests for POST /api/uncertainty."""

    @patch("app.routers.uncertainty.save_upload")
    @patch("app.routers.uncertainty.run_uncertainty")
    @patch("app.routers.uncertainty.path_to_url")
    def test_uncertainty_success(self, mock_url, mock_unc, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_unc.return_value = MOCK_UNCERTAINTY_RESULT.copy()
        mock_url.side_effect = lambda p: f"/files/{Path(p).name}"

        import asyncio

        from app.routers.uncertainty import uncertainty

        file = MagicMock()
        result = asyncio.run(uncertainty(file=file, model_name="unet", n_samples=10))

        assert result["task_id"] == "unc-001"
        assert mock_unc.called

    @patch("app.routers.uncertainty.save_upload")
    @patch("app.routers.uncertainty.run_uncertainty")
    @patch("app.routers.uncertainty.path_to_url")
    def test_uncertainty_default_params(self, mock_url, mock_unc, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_unc.return_value = MOCK_UNCERTAINTY_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.uncertainty import uncertainty

        file = MagicMock()
        asyncio.run(uncertainty(file=file, model_name="unet", n_samples=10))

        call_args = mock_unc.call_args
        assert call_args[0][1] == "unet"
        assert call_args[0][2] == 10

    @patch("app.routers.uncertainty.save_upload")
    @patch("app.routers.uncertainty.run_uncertainty")
    @patch("app.routers.uncertainty.path_to_url")
    def test_uncertainty_custom_n_samples(self, mock_url, mock_unc, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_unc.return_value = MOCK_UNCERTAINTY_RESULT.copy()
        mock_url.side_effect = lambda p: p

        import asyncio

        from app.routers.uncertainty import uncertainty

        file = MagicMock()
        asyncio.run(uncertainty(file=file, model_name="attention_unet", n_samples=25))

        call_args = mock_unc.call_args
        assert call_args[0][2] == 25

    @patch("app.routers.uncertainty.save_upload")
    @patch("app.routers.uncertainty.run_uncertainty")
    @patch("app.routers.uncertainty.path_to_url")
    def test_uncertainty_paths_converted(self, mock_url, mock_unc, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_unc.return_value = MOCK_UNCERTAINTY_RESULT.copy()
        mock_url.side_effect = lambda p: f"URL({p})"

        import asyncio

        from app.routers.uncertainty import uncertainty

        file = MagicMock()
        result = asyncio.run(uncertainty(file=file, model_name="unet", n_samples=10))

        assert result["mean_path"].startswith("URL(")
        assert result["std_path"].startswith("URL(")
        assert result["entropy_path"].startswith("URL(")

    @patch("app.routers.uncertainty.save_upload")
    @patch("app.routers.uncertainty.run_uncertainty")
    @patch("app.routers.uncertainty.path_to_url")
    def test_uncertainty_none_paths_not_converted(self, mock_url, mock_unc, mock_upload):
        mock_upload.return_value = Path("/tmp/img.tif")
        mock_unc.return_value = {
            "task_id": "unc-002",
            "mean_path": None,
            "std_path": None,
            "entropy_path": None,
        }
        mock_url.side_effect = lambda p: f"URL({p})"

        import asyncio

        from app.routers.uncertainty import uncertainty

        file = MagicMock()
        result = asyncio.run(uncertainty(file=file, model_name="unet", n_samples=10))

        assert result["mean_path"] is None
        assert result["std_path"] is None
        assert result["entropy_path"] is None
        mock_url.assert_not_called()
