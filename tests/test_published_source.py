"""Published MkDocs data remains searchable without a docs repository."""

import httpx
import pytest
from fastmcp import Client, FastMCP

from mkdocs_mcp.config import Settings
from mkdocs_mcp.context import AppContext
from mkdocs_mcp.sources import search_index_source
from mkdocs_mcp.tools import register_all


@pytest.fixture
def published_cfg():
    return Settings(
        source_mode="search_index",
        base_url="https://docs.example.com",
        search_index_url="https://docs.example.com/search/search_index.json",
        reindex_interval_minutes=0,
        embeddings_enabled=False,
        metrics_enabled=False,
        rate_limit_enabled=False,
    )


def _mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        search_index_source.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=transport, **kwargs),
    )


async def test_published_search_and_conditional_refresh(monkeypatch, published_cfg):
    requests = []

    def handler(request):
        requests.append(request)
        if request.headers.get("if-none-match") == '"first"':
            return httpx.Response(304)
        return httpx.Response(
            200,
            headers={"ETag": '"first"'},
            json={
                "config": {"lang": ["en"]},
                "docs": [
                    {"location": "guides/install/", "title": "Install", "text": ""},
                    {
                        "location": "guides/install/#run-it",
                        "title": "Run <code>it</code>",
                        "text": '<p>Apply this YAML:</p><pre><code class="language-yaml">'
                        "apiVersion: v1\n  kind: Pod\n</code></pre>",
                    },
                    {"location": "guides/other/", "title": "Other", "text": "Unrelated notes."},
                ],
            },
        )

    _mock_http(monkeypatch, handler)
    ctx = AppContext(published_cfg)
    first = await ctx.indexer.build()
    assert len(first.documents) == 2
    assert len(first.sections) == 3
    page = first.get_doc("guides/install")
    assert page.url == "https://docs.example.com/guides/install/"
    assert "apiVersion: v1" in page.content
    section = first.sections_of("guides/install")[1]
    assert section.url == "https://docs.example.com/guides/install/#run-it"
    assert section.heading == "Run it"
    assert section.code_blocks[0].language == "yaml"
    assert "  kind: Pod" in section.code_blocks[0].code
    assert ctx.engine.search("apply yaml")[0].url == section.url
    assert ctx.engine.search("install")[0].snippet

    mcp = FastMCP(name="published")
    register_all(mcp, ctx)
    async with Client(mcp) as client:
        result = await client.call_tool("get_page", {"page_id": "guides/install"})
        assert result.structured_content["result"]["url"] == page.url
        assert "apiVersion: v1" in result.structured_content["result"]["content"]
        outline = await client.call_tool("summarize_page", {"page_id": "guides/install"})
        assert outline.structured_content["result"]["sections"][1]["heading"] == "Run it"

    second = await ctx.indexer.build()
    assert second is first
    assert requests[1].headers["if-none-match"] == '"first"'


def test_unknown_terms_do_not_match_a_generic_word():
    from mkdocs_mcp.search.bm25 import BM25Index

    bm25 = BM25Index()
    bm25.build(
        [
            ("Topic guide", "This topic has details."),
            ("Installation", "Install the service."),
            ("Network Policy", "Apply a policy."),
        ]
    )
    assert bm25.search("foobar nonexistent topic") == []
    assert bm25.search("network policy")


async def test_failed_refresh_keeps_last_good_index(monkeypatch, published_cfg):
    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                headers={"ETag": '"first"'},
                json={"docs": [{"location": "", "title": "Home", "text": "Welcome"}]},
            )
        return httpx.Response(500)

    _mock_http(monkeypatch, handler)
    ctx = AppContext(published_cfg)
    first = await ctx.indexer.build()
    await ctx.indexer.safe_build()
    assert ctx.store is first
    assert first.get_doc("index").url == "https://docs.example.com/"
