"""Discovery tools: recent_changes, find_runbooks, find_examples."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel

from ..context import AppContext
from ..models import ChangeEntry, CodeBlock, PageRef


class ExampleHit(BaseModel):
    page_id: str
    heading: str
    url: str
    code_blocks: list[CodeBlock]


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def recent_changes(limit: int = 15, tenant: str | None = None) -> list[ChangeEntry]:
        """List the most recently modified documentation pages (from git
        history). Use for "what changed recently?". Requires the git source;
        returns an empty list otherwise."""
        ctx.ensure_loaded()
        docs = [
            d
            for d in ctx.store.documents.values()
            if d.last_modified and (not tenant or d.tenant == tenant)
        ]
        docs.sort(key=lambda d: d.last_modified or "", reverse=True)
        return [
            ChangeEntry(
                page_id=d.page_id,
                title=d.title,
                url=d.url,
                last_modified=d.last_modified,
                author=d.author,
            )
            for d in docs[:limit]
        ]

    @mcp.tool
    def find_runbooks(topic: str | None = None, tenant: str | None = None) -> list[PageRef]:
        """List operational runbooks (pages under runbooks/). Optionally filter
        by topic or tenant. Use for "what runbooks exist for X?"."""
        ctx.ensure_loaded()
        resolved = ctx.classifier.resolve_topic(topic) if topic else None
        out: list[PageRef] = []
        for d in ctx.store.documents.values():
            if not d.is_runbook:
                continue
            if tenant and d.tenant != tenant:
                continue
            if resolved and resolved not in d.topics:
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
    def find_examples(
        topic: str | None = None,
        language: str | None = None,
        limit: int = 15,
    ) -> list[ExampleHit]:
        """Find sections that contain code/command examples, optionally filtered
        by topic or code language (e.g. "bash", "yaml"). Use for "show me an
        example of …"."""
        ctx.ensure_loaded()
        resolved = ctx.classifier.resolve_topic(topic) if topic else None
        lang = language.lower() if language else None
        out: list[ExampleHit] = []
        for s in ctx.store.sections:
            if not s.code_blocks:
                continue
            if resolved and resolved not in s.topics:
                continue
            blocks = (
                [b for b in s.code_blocks if (b.language or "").lower() == lang]
                if lang
                else s.code_blocks
            )
            if not blocks:
                continue
            out.append(
                ExampleHit(page_id=s.page_id, heading=s.heading, url=s.url, code_blocks=blocks)
            )
            if len(out) >= limit:
                break
        return out
