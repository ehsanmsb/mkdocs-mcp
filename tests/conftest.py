import os

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def cfg():
    from mkdocs_mcp.config import Settings

    return Settings(
        source_mode="local",
        local_dir=FIXTURES,
        base_url="https://docs.test",
        reindex_interval_minutes=0,
        metrics_enabled=False,
        rate_limit_enabled=False,
    )


@pytest.fixture
async def ctx(cfg):
    from mkdocs_mcp.context import AppContext

    c = AppContext(cfg)
    await c.indexer.build()
    return c
