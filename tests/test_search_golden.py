"""Golden retrieval tests: a query must surface the expected page in the top-k.

These guard against ranking regressions as the engine evolves.
"""

import pytest

from mkdocs_mcp.search.engine import Filters

GOLDEN = [
    ("expose an http service with a hostname", "platform/networking/expose-service"),
    ("argocd gitops continuous delivery", "platform/argocd/user-guide"),
    ("migrate repository runbook", "platform/argocd/runbooks/migrate-repository"),
]


@pytest.mark.parametrize("query,expected", GOLDEN)
async def test_golden_topk(ctx, query, expected):
    hits = ctx.engine.search(query, Filters(), limit=3)
    assert any(h.page_id == expected for h in hits), [h.page_id for h in hits]


async def test_tenant_filter(ctx):
    hits = ctx.engine.search("service", Filters(tenant="platform"), limit=5)
    assert hits and all(h.tenant == "platform" for h in hits)


async def test_doc_type_filter_runbook(ctx):
    hits = ctx.engine.search("repository", Filters(doc_type="runbook"), limit=5)
    assert all(h.doc_type == "runbook" for h in hits)


async def test_topic_filter(ctx):
    hits = ctx.engine.search("login", Filters(topic="argocd"), limit=5)
    assert all("argocd" in (ctx.store.get_doc(h.page_id).topics) for h in hits)


async def test_empty_state(ctx):
    hits = ctx.engine.search("zzzznotatopic", Filters(), limit=5)
    es = hits or ctx.engine.empty_state("zzzznotatopic")
    assert es and "find_by_topic" in es[0].snippet
