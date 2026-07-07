"""Tests for the export router."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse


class TestExportEndpoint:
    """Test suite for the export_result endpoint."""

    @patch("app.routers.export.get_result")
    def test_export_not_found(self, mock_get):
        mock_get.return_value = None

        from app.routers.export import export_result

        with pytest.raises(HTTPException) as exc_info:
            export_result(task_id="abc", fmt="png")
        assert exc_info.value.status_code == 404

    @patch("app.routers.export.os.path.isfile")
    @patch("app.routers.export.get_result")
    def test_export_png_success(self, mock_get, mock_isfile):
        mock_get.return_value = {"task_id": "abc", "mask_path": "/tmp/m.npy"}
        import numpy as np
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
        np.save(tmp.name, np.zeros((10, 10, 2), dtype=np.float32))

        from app.routers.export import export_result

        with patch("app.routers.export.np.load", return_value=np.zeros((10, 10, 2))):
            with patch("app.routers.export.export_service.export_masks_png",
                       return_value={"file_paths": ["/tmp/test.png"]}):
                result = export_result(task_id="abc", fmt="png")
                assert isinstance(result, FileResponse)

    @patch("app.routers.export.os.path.isfile")
    @patch("app.routers.export.get_result")
    def test_export_npy_success(self, mock_get, mock_isfile):
        mock_get.return_value = {"task_id": "abc", "mask_path": "/tmp/m.npy"}
        mock_isfile.return_value = True

        from app.routers.export import export_result

        with patch("app.routers.export.np.load", return_value=np.zeros((10, 10, 2))):
            with patch("app.routers.export.export_service.export_masks_numpy",
                       return_value={"file_path": "/tmp/test.npy"}):
                result = export_result(task_id="abc", fmt="npy")
                assert isinstance(result, FileResponse)

    @patch("app.routers.export.get_result")
    def test_export_invalid_format(self, mock_get):
        mock_get.return_value = {"task_id": "abc", "mask_path": "/tmp/m.npy"}

        from app.routers.export import export_result

        with pytest.raises(HTTPException) as exc_info:
            export_result(task_id="abc", fmt="bmp")
        assert exc_info.value.status_code == 400

    @patch("app.routers.export.get_result")
    def test_export_service_error(self, mock_get):
        mock_get.return_value = {"task_id": "abc", "mask_path": "/tmp/m.npy"}

        from app.routers.export import export_result

        with patch("app.routers.export.os.path.isfile", return_value=True):
            with patch("app.routers.export.np.load", side_effect=ValueError("Corrupt file")):
                with pytest.raises(HTTPException) as exc_info:
                    export_result(task_id="abc", fmt="png")
                assert exc_info.value.status_code == 400

    def test_valid_formats_set(self):
        from app.routers.export import VALID_FORMATS

        assert "png" in VALID_FORMATS
        assert "npy" in VALID_FORMATS
        assert "csv" in VALID_FORMATS
        assert "json" in VALID_FORMATS
        assert "geojson" in VALID_FORMATS
        assert "geotiff" in VALID_FORMATS