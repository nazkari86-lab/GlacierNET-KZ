"""MCP exposes only evidence-backed tools and fails closed for old scaffolds."""

from __future__ import annotations

import pytest

from app import config, mcp_tools


def test_removed_research_tool_fails_closed():
    result = mcp_tools.execute_tool("analyze_glacier", {"image_path": "missing.tif"})

    assert result["status"] == "error"
    assert "Unknown or removed tool" in result["error"]


def test_catalog_contains_only_evidence_tools():
    names = {item["name"] for item in mcp_tools.get_tool_definitions()}

    assert names == {
        "analyze_registered_glacier",
        "compare_local_years",
        "get_ml_readiness",
        "get_model_info",
        "get_project_stats",
        "get_risk_twin_context",
        "inspect_glacier_timeseries",
        "inspect_local_year",
        "inspect_ml_case",
        "list_datasets",
        "list_local_years",
        "list_ml_cases",
        "list_models",
        "scan_regional_lakes",
        "search_glaciers",
    }
    assert not names & {
        "diffusion_sample",
        "graph_neural_network_predict",
        "run_ensemble_prediction",
        "vit_predict",
    }


def test_unknown_arguments_fail_closed():
    result = mcp_tools.execute_tool("list_local_years", {"invented": True})

    assert result["status"] == "error"
    assert "unexpected" in result["error"]


def test_heavy_mcp_inference_requires_explicit_opt_in(monkeypatch):
    monkeypatch.setattr(config, "MCP_INFERENCE_ENABLED", False)

    result = mcp_tools.execute_tool(
        "analyze_registered_glacier",
        {"rgi_id": "RGI2000-v7.0-G-13-33843", "year": 2024},
    )

    assert result["status"] == "error"
    assert "MCP inference is disabled" in result["error"]


@pytest.mark.local_data
def test_dataset_tool_lists_physical_local_files():
    result = mcp_tools.execute_tool("list_datasets", {"limit": 3})

    assert result["status"] == "success"
    assert result["data"]["datasets"]
    assert all(item["source_path"] for item in result["data"]["datasets"])


def test_verified_local_year_tools_use_real_tables():
    result = mcp_tools.execute_tool("inspect_local_year", {"year": 2024})

    assert result["status"] == "success"
    assert result["data"]["year"] == 2024
    assert result["data"]["quality_score"] < 100
    assert result["data"]["primary_area_km2"] == 450.47


def test_verified_year_comparison_preserves_caveats():
    result = mcp_tools.execute_tool(
        "compare_local_years",
        {"from_year": 2000, "to_year": 2024},
    )

    assert result["status"] == "success"
    assert result["data"]["change_km2"] == -128.61
    assert result["data"]["warnings"]


@pytest.mark.local_data
def test_glacier_tool_uses_physical_registry_and_masks():
    result = mcp_tools.execute_tool(
        "inspect_glacier_timeseries",
        {"rgi_id": "RGI2000-v7.0-G-13-33843", "method": "ndsi"},
    )

    assert result["status"] == "success"
    assert result["data"]["glacier"]["wgms_reference"] is True
    assert len(result["data"]["points"]) >= 16
    assert "fixed RGI 2000" in result["data"]["caveat"]
