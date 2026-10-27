import json
from pathlib import Path

import httpx
import pytest

from mkdocs_mcp.config import Settings, SiteConfig
from mkdocs_mcp.context import AppContext
from mkdocs_mcp.sources import search_index_source

FIXTURE = Path(__file__).parent / "fixtures" / "search_index.json"


@pytest.fixture
def cfg():
    return Settings(
        sites=[SiteConfig(name="docs", base_url="https://docs.test")],
        reindex_interval_minutes=0,
        metrics_enabled=False,
        rate_limit_enabled=False,
    )


@pytest.fixture
async def ctx(cfg, monkeypatch):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=data))
    monkeypatch.setattr(
        search_index_source.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=transport, **kwargs),
    )
    context = AppContext(cfg)
    await context.indexer.build()
    return context
