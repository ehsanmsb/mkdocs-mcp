"""Tool contract tests via an in-memory FastMCP client."""

import pytest
from fastmcp import Client, FastMCP

from mkdocs_mcp.tools import register_all


@pytest.fixture
async def client(ctx):
    mcp = FastMCP(name="test")
    register_all(mcp, ctx)
    return Client(mcp)


async def test_tools_registered(client):
    async with client:
        tools = {t.name for t in await client.list_tools()}
    expected = {
        "search_docs",
        "search_section",
        "get_page",
        "get_section",
        "list_pages",
        "summarize_page",
        "find_runbooks",
        "find_examples",
        "health_check",
        "get_statistics",
    }
    assert tools == expected
    assert "rebuild_index" not in tools
    assert "recent_changes" not in tools
    assert "browse_tree" not in tools


async def test_search_docs_tool(client):
    async with client:
        r = await client.call_tool("search_docs", {"query": "expose http service"})
    assert r.structured_content["result"][0]["page_id"] == "docs:platform/networking/expose-service"


async def test_no_match_has_no_placeholder_result(client):
    async with client:
        r = await client.call_tool("search_docs", {"query": "zzzznotatopic"})
    assert r.structured_content["result"] == []


async def test_search_section_returns_multiple_sections_from_one_page(client):
    async with client:
        r = await client.call_tool(
            "search_section",
            {"page_id": "docs:platform/argocd/user-guide", "query": "argo", "limit": 5},
        )
    hits = r.structured_content["result"]
    assert {"Overview", "CLI Login"} <= {hit["heading"] for hit in hits}


async def test_get_page_tool(client):
    async with client:
        r = await client.call_tool("get_page", {"page_id": "docs:platform/argocd/user-guide"})
    page = r.structured_content["result"]  # optional return wrapped under "result"
    assert page["title"].startswith("Argo")
    assert "GitOps" in page["content"]
    assert "tenant" not in page and "topics" not in page


async def test_find_runbooks(client):
    async with client:
        r = await client.call_tool("find_runbooks", {})
    ids = {p["page_id"] for p in r.structured_content["result"]}
    assert "docs:platform/argocd/runbooks/migrate-repository" in ids


async def test_find_examples_by_language(client):
    async with client:
        r = await client.call_tool("find_examples", {"language": "bash"})
    examples = r.structured_content["result"]
    assert len(examples) == 1
    assert "argocd login" in examples[0]["code_blocks"][0]["code"]


async def test_health_check(client):
    async with client:
        r = await client.call_tool("health_check", {})
    assert r.structured_content["index_loaded"] is True
    assert "vector_enabled" not in r.structured_content
