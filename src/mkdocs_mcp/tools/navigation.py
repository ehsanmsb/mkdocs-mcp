"""Read and list pages from the published search corpus."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..indexing.text import slugify
from ..models import PageContent, PageRef, SectionContent


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def get_page(page_id: str) -> PageContent | None:
        """Return page text from the published search index, plus its live URL.
        Use after search_docs to read a page or follow the URL for its rendered form."""
        ctx.ensure_loaded()
        d = ctx.store.get_doc(page_id)
        if not d:
            return None
        return PageContent(
            page_id=d.page_id,
            site=d.site,
            title=d.title,
            breadcrumb=[d.title],
            url=d.url,
            doc_type=d.doc_type,
            headings=d.headings,
            content=d.content,
        )

    @mcp.tool
    def get_section(page_id: str, heading: str) -> SectionContent | None:
        """Return one section of a page by its heading text, plus the adjacent
        section headings for context."""
        ctx.ensure_loaded()
        sections = ctx.store.sections_of(page_id)
        target = slugify(heading)
        for idx, s in enumerate(sections):
            if s.anchor == target or s.heading.lower() == heading.lower():
                return SectionContent(
                    page_id=page_id,
                    site=s.site,
                    heading=s.heading,
                    url=s.url,
                    text=s.text,
                    prev_heading=sections[idx - 1].heading if idx > 0 else None,
                    next_heading=(sections[idx + 1].heading if idx + 1 < len(sections) else None),
                )
        return None

    @mcp.tool
    def list_pages(
        doc_type: str | None = None,
    ) -> list[PageRef]:
        """List indexed published pages, optionally filtered by doc_type."""
        ctx.ensure_loaded()
        out: list[PageRef] = []
        for d in ctx.store.documents.values():
            if doc_type and d.doc_type != doc_type:
                continue
            out.append(
                PageRef(
                    page_id=d.page_id,
                    site=d.site,
                    title=d.title,
                    url=d.url,
                    doc_type=d.doc_type,
                )
            )
        out.sort(key=lambda p: p.page_id)
        return out
