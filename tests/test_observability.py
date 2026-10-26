"""Operational contracts for tool metrics and Helm environment settings."""

import re
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from prometheus_client import REGISTRY

from mkdocs_mcp.config import Settings
from mkdocs_mcp.obs.logging import setup_logging
from mkdocs_mcp.obs.metrics import ToolObservabilityMiddleware


async def test_tool_failure_is_counted_and_logged(capsys):
    setup_logging()
    before = (
        REGISTRY.get_sample_value(
            "mkdocs_mcp_tool_calls_total", {"tool": "fails", "status": "error"}
        )
        or 0
    )
    mcp = FastMCP("observability-test")
    mcp.add_middleware(ToolObservabilityMiddleware(True))

    @mcp.tool
    def fails() -> str:
        raise ValueError("invalid fixture")

    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("fails", {})

    assert (
        REGISTRY.get_sample_value(
            "mkdocs_mcp_tool_calls_total", {"tool": "fails", "status": "error"}
        )
        == before + 1
    )
    logs = capsys.readouterr()
    assert logs.out.count('"event": "tool_failed"') == 1
    assert "Error calling tool" not in logs.err


def test_helm_maps_every_setting():
    template = (
        Path(__file__).parents[1] / "charts/mkdocs-mcp/templates/configmap.yaml"
    ).read_text()
    mapped = set(re.findall(r"^\s+(MKDOCS_MCP_[A-Z_]+):", template, re.MULTILINE))
    expected = {f"MKDOCS_MCP_{name.upper()}" for name in Settings.model_fields}
    assert mapped == expected
