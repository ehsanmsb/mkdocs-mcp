"""Discover runbooks and code examples in published documentation."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel

from ..context import AppContext
from ..models import CodeBlock, PageRef


class ExampleHit(BaseModel):
    page_id: str
    site: str = ""
    heading: str
    url: str
    code_blocks: list[CodeBlock]


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool
    def find_runbooks() -> list[PageRef]:
        """List operational runbooks (pages under runbooks/)."""
        ctx.ensure_loaded()
        out: list[PageRef] = []
        for d in ctx.store.documents.values():
            if d.doc_type != "runbook":
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

    @mcp.tool
    def find_examples(
        language: str | None = None,
        limit: int = 15,
    ) -> list[ExampleHit]:
        """Find sections that contain code/command examples, optionally filtered
        by code language (e.g. "bash", "yaml"). Use for "show me an
        example of …"."""
        ctx.ensure_loaded()
        if limit <= 0:
            return []
        lang = language.lower() if language else None
        out: list[ExampleHit] = []
        for s in ctx.store.sections:
            if not s.code_blocks:
                continue
            blocks = (
                [b for b in s.code_blocks if (b.language or "").lower() == lang]
                if lang
                else s.code_blocks
            )
            if not blocks:
                continue
            out.append(
                ExampleHit(
                    page_id=s.page_id,
                    site=s.site,
                    heading=s.heading,
                    url=s.url,
                    code_blocks=blocks,
                )
            )
            if len(out) >= limit:
                break
        return out
