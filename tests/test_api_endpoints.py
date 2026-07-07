"""Tests for API routers — /api/models, /api/models/available, /health."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "glacierkz-api"))


class TestModelsRouter:
    """Tests for /api/models endpoint."""

    def test_list_models_returns_available_only(self):
        from app.routers.models import list_models

        result = list_models()
        assert len(result) > 0
        for model in result:
            assert model.get("available") is True
            assert "name" in model
            assert "display_name" in model

    def test_list_all_models_includes_unavailable_flag(self):
        from app.routers.models import list_all_models

        result = list_all_models()
        assert len(result) >= 3
        assert all("available" in m for m in result)

    def test_catalog_has_required_fields(self):
        from app.routers.models import MODELS_CATALOG
        for model in MODELS_CATALOG:
            assert "name" in model
            assert "display_name" in model
            assert "description" in model
            assert "supports_tta" in model
            assert "supports_crf" in model
            assert "supports_uncertainty" in model

    def test_catalog_contains_known_models(self):
        from app.routers.models import MODELS_CATALOG
        names = [m["name"] for m in MODELS_CATALOG]
        assert "unet" in names
        assert "attention_unet" in names
        assert "unet_plus_plus" in names
        assert "ndsi" in names
        assert "rf" in names
        assert "ensemble" in names

    def test_list_available_architectures(self):
        from app.routers.models import list_available_architectures
        result = list_available_architectures()
        assert isinstance(result, list)
        assert len(result) >= 3
        names = [r["name"] for r in result]
        assert "unet" in names
        assert "attention_unet" in names
        assert "unet_plus_plus" in names


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self):
        from app.main import health
        result = health()
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"
        assert result["service"] == "GlacierNET-KZ API"
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0


class TestRootEndpoint:
    """Tests for / endpoint."""

    def test_root_returns_info(self):
        from app.main import root
        result = root()
        if isinstance(result, dict):
            assert "name" in result or "GlacierNET" in str(result)
        else:
            from starlette.responses import Response
            assert isinstance(result, Response)
