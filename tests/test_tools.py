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
        "search_docs", "search_section", "semantic_search",
        "get_page", "get_section", "list_categories", "list_pages", "browse_tree",
        "summarize_page", "related_documents", "suggest_reading",
        "recent_changes", "find_runbooks", "find_examples",
        "find_by_topic", "find_argocd_docs",
        "rebuild_index", "health_check", "get_statistics",
    }
    assert expected <= tools


async def test_search_docs_tool(client):
    async with client:
        r = await client.call_tool("search_docs", {"query": "expose http service"})
    assert r.structured_content["result"][0]["page_id"] == "platform/networking/expose-service"


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
