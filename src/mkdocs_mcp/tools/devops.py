"""Topic-oriented tools.

One parameterized finder (``find_by_topic``) backed by the configured topic
vocabulary, plus thin ``find_<topic>_docs`` aliases generated from
``settings.featured_topics`` (so users can name a topic directly). The aliases
add no logic of their own and are fully configuration-driven — no topic names
are hardcoded here.
"""

from __future__ import annotations

from fastmcp import FastMCP

from ..context import AppContext
from ..models import PageRef


def _topic_pages(ctx: AppContext, topic: str, doc_type: str | None) -> list[PageRef]:
    resolved = ctx.classifier.resolve_topic(topic)
    out: list[PageRef] = []
    if not resolved:
        return out
    for d in ctx.store.documents.values():
        if resolved not in d.topics:
            continue
        if doc_type and d.doc_type != doc_type:
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


def register(mcp: FastMCP, ctx: AppContext) -> None:
    vocab = ctx.classifier.vocab
    find_by_topic_desc = (
        "List all documentation pages for a topic.\n\n"
        f"Available topics: {', '.join(vocab)}.\n"
        "Common aliases are accepted (k8s->kubernetes, okd->openshift, "
        "argo->argocd, tf->terraform). Optionally filter by doc_type "
        "(guide | runbook | tutorial | troubleshooting | reference)."
    )

    @mcp.tool(description=find_by_topic_desc)
    def find_by_topic(topic: str, doc_type: str | None = None) -> list[PageRef]:
        ctx.ensure_loaded()
        return _topic_pages(ctx, topic, doc_type)

    # Generate convenience aliases for the configured featured topics.
    def _make_alias(topic: str) -> None:
        desc = f"List all {topic} documentation. Alias for find_by_topic('{topic}')."

        @mcp.tool(name=f"find_{topic.replace('-', '_')}_docs", description=desc)
        def _alias(doc_type: str | None = None) -> list[PageRef]:
            ctx.ensure_loaded()
            return _topic_pages(ctx, topic, doc_type)

    seen: set[str] = set()
    for topic in ctx.cfg.featured_topics:
        canonical = ctx.classifier.resolve_topic(topic)
        if canonical and canonical not in seen:
            seen.add(canonical)
            _make_alias(canonical)
