"""Navigation tools: get_page, get_section, list_categories, list_pages, browse_tree."""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..indexing.text import slugify
from ..models import PageContent, PageRef, SectionContent, TreeNode


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def get_page(page_id: str) -> PageContent | None:
        """Return the full content + metadata of a documentation page by its
        page_id (e.g. "guides/deployment"). Use after a search to read the
        whole page."""
        ctx.ensure_loaded()
        d = ctx.store.get_doc(page_id)
        if not d:
            return None
        return PageContent(
            page_id=d.page_id,
            title=d.title,
            breadcrumb=d.breadcrumb + [d.title],
            url=d.url,
            edit_url=d.edit_url,
            tenant=d.tenant,
            doc_type=d.doc_type,
            topics=d.topics,
            headings=d.headings,
            last_modified=d.last_modified,
            author=d.author,
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
                    heading=s.heading,
                    url=s.url,
                    text=s.text,
                    prev_heading=sections[idx - 1].heading if idx > 0 else None,
                    next_heading=(sections[idx + 1].heading if idx + 1 < len(sections) else None),
                )
        return None

    @mcp.tool
    def list_categories(tenant: str | None = None) -> list[TreeNode]:
        """List the top-level navigation categories (from the MkDocs nav).
        Optionally scope to one tenant (top-level section)."""
        ctx.ensure_loaded()
        roots = ctx.store.tree(tenant)
        return [TreeNode(title=r.title, children=r.children) for r in roots]

    @mcp.tool
    def list_pages(
        category: str | None = None,
        tenant: str | None = None,
        doc_type: str | None = None,
    ) -> list[PageRef]:
        """List pages, optionally filtered by tenant, doc_type, or a category
        name (matched against the navigation breadcrumb)."""
        ctx.ensure_loaded()
        out: list[PageRef] = []
        for d in ctx.store.documents.values():
            if tenant and d.tenant != tenant:
                continue
            if doc_type and d.doc_type != doc_type:
                continue
            if category and category.lower() not in [c.lower() for c in d.breadcrumb]:
                continue
            out.append(
                PageRef(
                    page_id=d.page_id,
                    title=d.title,
                    url=d.url,
                    doc_type=d.doc_type,
                    tenant=d.tenant,
                    topics=d.topics,
                )
            )
        out.sort(key=lambda p: p.page_id)
        return out

    @mcp.tool
    def browse_tree(tenant: str | None = None) -> list[TreeNode]:
        """Return the full hierarchical navigation tree (categories and pages),
        optionally scoped to a tenant. Use to explore what documentation
        exists."""
        ctx.ensure_loaded()
        return ctx.store.tree(tenant)
