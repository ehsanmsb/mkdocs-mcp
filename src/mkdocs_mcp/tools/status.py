"""Read-only health and corpus statistics tools."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..models import HealthStatus, Statistics


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def health_check() -> HealthStatus:
        """Report server health, index age, and semantic search status."""
        store = ctx.store
        return HealthStatus(
            status="ok" if store.is_loaded else "degraded",
            index_loaded=store.is_loaded,
            index_age_seconds=store.index_age_seconds(),
            pages=len(store.documents),
            sections=len(store.sections),
            last_commit=store.commit,
            vector_enabled=ctx.engine.vector_enabled,
        )

    @mcp.tool
    def get_statistics() -> Statistics:
        """Return corpus counts by tenant, doc type, and topic."""
        ctx.ensure_loaded()
        return ctx.store.statistics()
