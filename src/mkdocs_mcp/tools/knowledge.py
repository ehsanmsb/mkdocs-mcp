"""Knowledge tools: summarize_page, related_documents, suggest_reading.

Summarization is intentionally client-side: these tools return structured
content + outlines for the calling LLM to summarize. We do not embed an LLM in
the server (no extra model dependency, no token cost, no external API).
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel

from ..context import AppContext
from ..models import ReadingItem, SearchHit
from ..search.engine import Filters


class PageOutline(BaseModel):
    page_id: str
    title: str
    url: str
    headings: list[str]
    sections: list[dict]  # [{heading, text}]
    note: str


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def summarize_page(page_id: str) -> PageOutline | None:
        """Return a page's outline + section texts so you (the assistant) can
        summarize it for the user. Pass a page_id from a prior search."""
        ctx.ensure_loaded()
        d = ctx.store.get_doc(page_id)
        if not d:
            return None
        sections = [{"heading": s.heading, "text": s.text} for s in ctx.store.sections_of(page_id)]
        return PageOutline(
            page_id=d.page_id,
            title=d.title,
            url=d.url,
            headings=d.headings,
            sections=sections,
            note="Summarize these sections for the user; cite the page URL.",
        )

    @mcp.tool
    def related_documents(
        page_id: str | None = None,
        query: str | None = None,
        limit: int = 5,
    ) -> list[SearchHit]:
        """Find documents related to a given page (by page_id) or to a free-text
        query. Useful for "what else should I read about this?"."""
        ctx.ensure_loaded()
        if page_id:
            return ctx.engine.related(page_id, limit=limit)
        if query:
            return ctx.engine.search(query, Filters(), limit=limit, mode="hybrid")
        return []

    @mcp.tool
    def suggest_reading(topic: str, limit: int = 8) -> list[ReadingItem]:
        """Build an ordered learning path for a topic: overview/guides first,
        then tutorials, then runbooks. Topic is matched to the known
        vocabulary (see find_by_topic)."""
        ctx.ensure_loaded()
        resolved = ctx.classifier.resolve_topic(topic) or topic
        order = {"guide": 0, "tutorial": 1, "reference": 2, "troubleshooting": 3, "runbook": 4}
        pages = [d for d in ctx.store.documents.values() if resolved in d.topics]
        pages.sort(key=lambda d: (order.get(d.doc_type, 9), d.page_id))
        return [
            ReadingItem(
                order=i,
                page_id=d.page_id,
                title=d.title,
                url=d.url,
                doc_type=d.doc_type,
                why=f"{d.doc_type} for {resolved}",
            )
            for i, d in enumerate(pages[:limit], start=1)
        ]
