"""Multiple published MkDocs sites share one searchable corpus."""

import json

import httpx
import pytest
from fastmcp import Client, FastMCP
from pydantic import ValidationError

from mkdocs_mcp.config import Settings, SiteConfig
from mkdocs_mcp.context import AppContext
from mkdocs_mcp.sources import search_index_source
from mkdocs_mcp.tools import register_all


def _settings() -> Settings:
    return Settings(
        sites=[
            SiteConfig(name="atlas", base_url="https://atlas.example.com"),
            SiteConfig(name="team", base_url="https://team.example.com"),
        ],
        reindex_interval_minutes=0,
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


def _index(text: str):
    return {"docs": [{"location": "guides/install/", "title": "Install", "text": text}]}


async def test_searches_all_sites_with_unique_page_ids_and_links(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request.url)
        text = "Deploy the cluster" if request.url.host == "atlas.example.com" else "Pay invoices"
        return httpx.Response(200, json=_index(text))

    _mock_http(monkeypatch, handler)
    ctx = AppContext(_settings())
    await ctx.indexer.build()

    assert {url.host for url in requests} == {"atlas.example.com", "team.example.com"}
    assert set(ctx.store.documents) == {"atlas:guides/install", "team:guides/install"}
    assert ctx.store.statistics().by_site == {"atlas": 1, "team": 1}
    assert ctx.engine.search("cluster")[0].site == "atlas"
    assert ctx.engine.search("invoices")[0].site == "team"

    mcp = FastMCP("multi-site")
    register_all(mcp, ctx)
    async with Client(mcp) as client:
        hits = await client.call_tool("search_docs", {"query": "install"})
        assert {hit["site"] for hit in hits.structured_content["result"]} == {"atlas", "team"}
        filtered = await client.call_tool("search_docs", {"query": "install", "site": "team"})
        assert [hit["page_id"] for hit in filtered.structured_content["result"]] == [
            "team:guides/install"
        ]
        page = await client.call_tool("get_page", {"page_id": "team:guides/install"})
        assert (
            page.structured_content["result"]["url"] == "https://team.example.com/guides/install/"
        )


async def test_failed_site_keeps_last_good_corpus_and_recovers(monkeypatch):
    fail_team = False
    update_team = False

    def handler(request):
        if request.url.host == "team.example.com" and fail_team:
            return httpx.Response(503)
        if request.url.host == "team.example.com" and update_team:
            return httpx.Response(
                200, headers={"ETag": '"second"'}, json=_index("Updated team handbook")
            )
        if request.headers.get("if-none-match") == '"first"':
            return httpx.Response(304)
        return httpx.Response(200, headers={"ETag": '"first"'}, json=_index(request.url.host))

    _mock_http(monkeypatch, handler)
    ctx = AppContext(_settings())
    first = await ctx.indexer.build()
    fail_team = True
    assert await ctx.indexer.build() is first
    assert ctx.indexer.failed_sites == ["team"]
    assert len(ctx.store.documents) == 2

    fail_team = False
    update_team = True
    refreshed = await ctx.indexer.build()
    assert refreshed is not first
    assert "Updated team handbook" in refreshed.get_doc("team:guides/install").content
    assert refreshed.get_doc("atlas:guides/install").url == (
        "https://atlas.example.com/guides/install/"
    )
    assert ctx.indexer.failed_sites == []


async def test_one_unavailable_site_does_not_block_startup(monkeypatch):
    def handler(request):
        if request.url.host == "atlas.example.com":
            return httpx.Response(304)  # No local copy exists yet.
        return httpx.Response(200, json=_index("Team handbook"))

    _mock_http(monkeypatch, handler)
    ctx = AppContext(_settings())
    await ctx.indexer.build()
    assert set(ctx.store.documents) == {"team:guides/install"}
    assert ctx.indexer.failed_sites == ["atlas"]

    mcp = FastMCP("partial")
    register_all(mcp, ctx)
    async with Client(mcp) as client:
        health = await client.call_tool("health_check", {})
    assert health.structured_content["status"] == "degraded"
    assert health.structured_content["loaded_sites"] == ["team"]


def test_sites_parse_from_environment_and_reject_duplicate_names(monkeypatch):
    monkeypatch.delenv("MKDOCS_MCP_SITES", raising=False)
    with pytest.raises(ValidationError, match="sites"):
        Settings(_env_file=None)
    monkeypatch.setenv("MKDOCS_MCP_SITES", "[]")
    with pytest.raises(ValidationError, match="at least 1"):
        Settings(_env_file=None)
    monkeypatch.setenv(
        "MKDOCS_MCP_SITES",
        json.dumps([{"name": "atlas", "base_url": "https://atlas.example.com"}]),
    )
    assert Settings(_env_file=None).sites[0].name == "atlas"
    with pytest.raises(ValidationError, match="unique"):
        Settings(
            sites=[
                SiteConfig(name="atlas", base_url="https://one.example"),
                SiteConfig(name="atlas", base_url="https://two.example"),
            ]
        )
    with pytest.raises(ValidationError, match="HTTP"):
        SiteConfig(name="unsafe", base_url="file:///etc/passwd")
    with pytest.raises(ValidationError, match="query or fragment"):
        SiteConfig(name="invalid", base_url="https://docs.example.com/?q=test")
