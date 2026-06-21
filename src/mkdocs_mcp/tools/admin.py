"""Administration tools: rebuild_index, health_check, get_statistics."""
from __future__ import annotations

import time

from fastmcp import FastMCP

from ..auth import require_admin
from ..context import AppContext
from ..models import HealthStatus, RebuildResult, Statistics


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    async def rebuild_index() -> RebuildResult:
        """Force a re-index: pull the latest docs and rebuild the search index.
        Use after docs are updated. May take a few seconds. (Admin scope.)"""
        require_admin()
        t0 = time.time()
        store = await ctx.indexer.build()
        return RebuildResult(
            status="ok",
            pages=len(store.documents),
            sections=len(store.sections),
            duration_ms=int((time.time() - t0) * 1000),
            commit=store.commit,
        )

    @mcp.tool
    def health_check() -> HealthStatus:
        """Report server health: whether the index is loaded, its age, the
        indexed commit, and whether semantic search is enabled."""
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
        """Return corpus statistics: counts by tenant, doc_type, and topic, plus
        the indexed commit and build time."""
        ctx.ensure_loaded()
        return ctx.store.statistics()
