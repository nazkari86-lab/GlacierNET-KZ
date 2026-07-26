"""MCP research scaffolds must never fabricate production-looking results."""

from __future__ import annotations

import pytest

from app import mcp_tools


def test_unvalidated_research_tool_fails_closed(monkeypatch):
    monkeypatch.delenv(mcp_tools.RESEARCH_TOOLS_ENV, raising=False)

    result = mcp_tools.execute_tool("analyze_glacier", {"image_path": "missing.tif"})

    assert result["status"] == "error"
    assert "unvalidated research scaffold" in result["error"]


def test_unvalidated_tools_are_visibly_labeled():
    definitions = {item["name"]: item for item in mcp_tools.get_tool_definitions()}

    for name in mcp_tools.UNVALIDATED_RESEARCH_TOOLS:
        assert definitions[name]["description"].startswith("[DISABLED BY DEFAULT:")


def test_verified_local_year_tools_use_real_tables():
    result = mcp_tools.execute_tool("inspect_local_year", {"year": 2024})

    assert result["status"] == "success"
    assert result["data"]["year"] == 2024
    assert result["data"]["quality_score"] == 100
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
