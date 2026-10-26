"""Tool registration aggregator."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from . import devops, discovery, knowledge, navigation, search, status


def register_all(mcp: FastMCP, ctx: AppContext) -> None:
    search.register(mcp, ctx)
    navigation.register(mcp, ctx)
    knowledge.register(mcp, ctx)
    discovery.register(mcp, ctx)
    devops.register(mcp, ctx)
    status.register(mcp, ctx)
