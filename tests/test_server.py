"""HTTP startup smoke test for the configured FastMCP server."""

from starlette.testclient import TestClient

from mkdocs_mcp.server import create_app
from mkdocs_mcp.ui import home_page


def test_http_health_and_readiness(cfg, ctx):
    app = create_app(cfg)
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        home = client.get("/", headers={"accept": "text/html"})
        browser_mcp = client.get("/mcp", headers={"accept": "text/html"})
        protocol_mcp = client.get("/mcp", headers={"accept": "application/json"})
        browser_missing = client.get("/missing", headers={"accept": "text/html"})
        api_missing = client.get("/missing", headers={"accept": "application/json"})

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "index_loaded": True}
    assert home.status_code == 200
    assert "MkDocs Docs" in home.text and "Pages indexed" in home.text
    assert browser_mcp.status_code == 200
    assert "text/html" in browser_mcp.headers["content-type"]
    assert "text/html" not in protocol_mcp.headers["content-type"]
    assert browser_missing.status_code == 404 and "Page not found" in browser_missing.text
    assert api_missing.status_code == 404 and api_missing.json() == {"error": "Not found"}


def test_landing_page_escapes_configured_name(cfg, ctx):
    cfg.server_name = '<script>alert("x")</script>'
    page = home_page(cfg, ctx)
    assert "<script>alert" not in page
    assert "&lt;script&gt;" in page
