"""Return page content for the MCP client to summarize.

Summarization is intentionally client-side: these tools return structured
content + outlines for the calling LLM to summarize. We do not embed an LLM in
the server (no extra model dependency, no token cost, no external API).
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel

from ..context import AppContext


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
