"""Search the published documentation by keyword."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..models import SearchHit
from ..search.engine import Filters


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def search_docs(
        query: str,
        doc_type: str | None = None,
        limit: int = 10,
        site: str | None = None,
    ) -> list[SearchHit]:
        """Search all configured documentation sites. Use this first for any "how do I…",
        "where is…", or general question. For non-English questions about English
        docs, translate the important search terms into English first.

        Returns the most relevant sections with title, breadcrumb, a deep-link
        URL, and a snippet. Optional doc_type filter: guide, runbook,
        tutorial, troubleshooting, or reference. Optional site filter uses a
        configured site name. Empty results mean no match.
        """
        ctx.ensure_loaded()
        return ctx.engine.search(query, Filters(doc_type=doc_type, site=site), limit=limit)

    @mcp.tool
    def search_section(page_id: str, query: str, limit: int = 5) -> list[SearchHit]:
        """Search within a single page's sections. Use to drill into a page you
        already found (pass its page_id, e.g. "guides/deployment")."""
        ctx.ensure_loaded()
        if not ctx.store.get_doc(page_id):
            return []
        return ctx.engine.search(query, Filters(page_id=page_id), limit=limit, dedupe_pages=False)
