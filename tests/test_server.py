"""HTTP startup smoke test for the configured FastMCP server."""

from starlette.testclient import TestClient

from mkdocs_mcp.server import create_app


def test_http_health_and_readiness(cfg, ctx):
    app = create_app(cfg)
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "index_loaded": True}
