"""Tool registration aggregator."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from . import admin, devops, discovery, knowledge, navigation, search


def register_all(mcp: FastMCP, ctx: AppContext) -> None:
    search.register(mcp, ctx)
    navigation.register(mcp, ctx)
    knowledge.register(mcp, ctx)
    discovery.register(mcp, ctx)
    devops.register(mcp, ctx)
    admin.register(mcp, ctx)
