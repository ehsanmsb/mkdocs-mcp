"""Tool contract tests via an in-memory FastMCP client."""

import pytest
from fastmcp import Client, FastMCP

from mkdocs_mcp.context import AppContext
from mkdocs_mcp.tools import register_all


@pytest.fixture
async def client(cfg):
    mcp = FastMCP(name="test")
    ctx = AppContext(cfg)
    await ctx.indexer.build()
    register_all(mcp, ctx)
    return Client(mcp)


async def test_tools_registered(client):
    async with client:
        tools = {t.name for t in await client.list_tools()}
    expected = {
        "search_docs",
        "search_section",
        "semantic_search",
        "get_page",
        "get_section",
        "list_pages",
        "summarize_page",
        "related_documents",
        "suggest_reading",
        "find_runbooks",
        "find_examples",
        "find_by_topic",
        "find_argocd_docs",
        "health_check",
        "get_statistics",
    }
    assert expected <= tools
    assert "rebuild_index" not in tools
    assert "recent_changes" not in tools
    assert "browse_tree" not in tools


async def test_search_docs_tool(client):
    async with client:
        r = await client.call_tool("search_docs", {"query": "expose http service"})
    assert r.structured_content["result"][0]["page_id"] == "platform/networking/expose-service"


async def test_search_section_returns_multiple_sections_from_one_page(client):
    async with client:
        r = await client.call_tool(
            "search_section",
            {"page_id": "platform/argocd/user-guide", "query": "argo", "limit": 5},
        )
    hits = r.structured_content["result"]
    assert len(hits) == 2
    assert {hit["heading"] for hit in hits} == {"Overview", "CLI Login"}


@pytest.mark.parametrize(
    "tool", ["search_docs", "semantic_search", "find_runbooks", "find_examples"]
)
async def test_unknown_topic_does_not_remove_filter(client, tool):
    args = {"topic": "not-a-topic"}
    if tool in {"search_docs", "semantic_search"}:
        args["query"] = "argocd"
    async with client:
        r = await client.call_tool(tool, args)
    assert r.structured_content["result"] == []


async def test_get_page_tool(client):
    async with client:
        r = await client.call_tool("get_page", {"page_id": "platform/argocd/user-guide"})
    page = r.structured_content["result"]  # optional return wrapped under "result"
    assert page["title"].startswith("Argo")
    assert "GitOps" in page["content"]


async def test_find_by_topic_alias(client):
    async with client:
        r = await client.call_tool("find_argocd_docs", {})
    ids = {p["page_id"] for p in r.structured_content["result"]}
    assert "platform/argocd/user-guide" in ids


async def test_find_runbooks(client):
    async with client:
        r = await client.call_tool("find_runbooks", {})
    ids = {p["page_id"] for p in r.structured_content["result"]}
    assert "platform/argocd/runbooks/migrate-repository" in ids


async def test_health_check(client):
    async with client:
        r = await client.call_tool("health_check", {})
    assert r.structured_content["index_loaded"] is True
