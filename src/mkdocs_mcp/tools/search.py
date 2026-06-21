"""Search tools: search_docs, search_section, semantic_search."""
from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..models import SearchHit
from ..search.engine import Filters


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def search_docs(
        query: str,
        tenant: str | None = None,
        doc_type: str | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Search the documentation. Use this first for any "how do I…",
        "where is…", or topic question.

        Returns the most relevant sections with title, breadcrumb, a deep-link
        URL, and a snippet. Optional filters:
          - tenant: a top-level section of the docs
          - doc_type: guide | runbook | tutorial | troubleshooting | reference
          - topic: a known technology topic (see find_by_topic for the list)
        """
        ctx.ensure_loaded()
        f = Filters(
            tenant=tenant,
            doc_type=doc_type,
            topic=ctx.classifier.resolve_topic(topic) if topic else None,
        )
        hits = ctx.engine.search(query, f, limit=limit, mode="hybrid")
        return hits or ctx.engine.empty_state(query)

    @mcp.tool
    def search_section(page_id: str, query: str, limit: int = 5) -> list[SearchHit]:
        """Search within a single page's sections. Use to drill into a page you
        already found (pass its page_id, e.g. "guides/deployment")."""
        ctx.ensure_loaded()
        if not ctx.store.get_doc(page_id):
            return []
        hits = ctx.engine.search(query, Filters(), limit=50, mode="lexical")
        return [h for h in hits if h.page_id == page_id][:limit]

    @mcp.tool
    def semantic_search(
        query: str,
        tenant: str | None = None,
        doc_type: str | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[SearchHit]:
        """Semantic / conceptual search (vector-based). Use for paraphrased or
        intent questions where exact keywords may not appear. Falls back to
        keyword search if the semantic layer is disabled."""
        ctx.ensure_loaded()
        f = Filters(
            tenant=tenant,
            doc_type=doc_type,
            topic=ctx.classifier.resolve_topic(topic) if topic else None,
        )
        mode = "semantic" if ctx.engine.vector_enabled else "lexical"
        hits = ctx.engine.search(query, f, limit=limit, mode=mode)
        return hits or ctx.engine.empty_state(query)
