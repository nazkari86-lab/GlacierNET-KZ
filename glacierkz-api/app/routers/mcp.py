# -*- coding: utf-8 -*-
"""MCP (Model Context Protocol) router for GlacierNET-KZ.

Exposes ML tools as MCP-compatible endpoints that can be called by LLM
agents or any MCP client.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.mcp_tools import execute_tool, get_tool_definitions

log = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class MCPToolCallRequest(BaseModel):
    """Request to call an MCP tool."""

    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPToolCallResponse(BaseModel):
    """Response from an MCP tool call."""

    status: str
    data: Any = None
    error: str | None = None


class MCPToolDef(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    inputSchema: dict[str, Any]


class MCPToolsListResponse(BaseModel):
    """Response listing all available MCP tools."""

    tools: list[MCPToolDef]
    count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tools", response_model=MCPToolsListResponse)
def list_tools() -> MCPToolsListResponse:
    """List all available MCP tools with their schemas."""
    defs = get_tool_definitions()
    return MCPToolsListResponse(
        tools=[MCPToolDef(**d) for d in defs],
        count=len(defs),
    )


@router.post("/tools/call", response_model=MCPToolCallResponse)
def call_tool(body: MCPToolCallRequest) -> MCPToolCallResponse:
    """Call an MCP tool by name with arguments."""
    result = execute_tool(body.tool_name, body.arguments)
    return MCPToolCallResponse(
        status=result.get("status", "error"),
        data=result.get("data"),
        error=result.get("error"),
    )


@router.get("/health")
def mcp_health() -> dict[str, Any]:
    """MCP service health check."""
    defs = get_tool_definitions()
    return {
        "status": "ok",
        "tools_available": len(defs),
        "tool_names": [d["name"] for d in defs],
    }
