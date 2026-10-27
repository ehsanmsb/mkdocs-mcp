"""Assemble the FastMCP app.

Tool failures and metrics are recorded by one middleware; FastMCP handles the
protocol and rate limiting. Browser routes remain separate from the MCP endpoint.
"""

from __future__ import annotations

import contextlib

from fastmcp import FastMCP
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from .config import Settings, get_settings
from .context import AppContext
from .obs import metrics
from .obs.logging import setup_logging
from .obs.metrics import ToolObservabilityMiddleware
from .tools import register_all
from .ui import home_page, not_found_page


class BrowserMCPMiddleware:
    """Show the landing page to browsers without changing MCP GET requests."""

    def __init__(self, app, cfg: Settings, ctx: AppContext) -> None:  # noqa: ANN001
        self.app = app
        self.cfg = cfg
        self.ctx = ctx

    async def __call__(self, scope, receive, send):  # noqa: ANN001
        if scope["type"] == "http" and scope["method"] == "GET" and scope["path"] == "/mcp":
            accept = Headers(scope=scope).get("accept", "")
            if "text/html" in accept and "text/event-stream" not in accept:
                response = HTMLResponse(home_page(self.cfg, self.ctx))
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def build_server(cfg: Settings | None = None) -> tuple[FastMCP, AppContext]:
    cfg = cfg or get_settings()
    setup_logging(cfg.log_level, cfg.log_json)

    mcp = FastMCP(
        name=cfg.server_name,
        instructions=(
            "Search the documentation with search_docs. Use search_section to narrow "
            "a result, get_page to read it, and find_runbooks or find_examples when "
            "needed. For questions in another language, search using relevant terms "
            "from the documentation's language. Results identify their site; use the "
            "site filter when needed. Cite returned page URLs."
        ),
    )

    mcp.add_middleware(ToolObservabilityMiddleware(cfg.metrics_enabled))
    if cfg.rate_limit_enabled:
        mcp.add_middleware(
            RateLimitingMiddleware(
                max_requests_per_second=cfg.rate_limit_per_second,
                burst_capacity=cfg.rate_limit_burst,
            )
        )

    ctx = AppContext(cfg)
    register_all(mcp, ctx)

    @mcp.custom_route("/", methods=["GET"])
    async def home(_request: Request) -> HTMLResponse:
        return HTMLResponse(home_page(cfg, ctx))

    @mcp.custom_route("/health", methods=["GET"])
    @mcp.custom_route("/livez", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/ready", methods=["GET"])
    @mcp.custom_route("/readyz", methods=["GET"])
    async def ready(_request: Request) -> JSONResponse:
        loaded = ctx.store.is_loaded
        failed = ctx.indexer.failed_sites
        return JSONResponse(
            {
                "status": "degraded" if loaded and failed else "ok" if loaded else "starting",
                "index_loaded": loaded,
            },
            status_code=200 if loaded else 503,
        )

    return mcp, ctx


async def _startup_index(ctx: AppContext) -> None:
    await ctx.indexer.build()
    ctx.indexer.start_scheduler()


def create_app(cfg: Settings | None = None):
    """Return the ASGI app for streamable-http (uvicorn / gunicorn entrypoint)."""
    cfg = cfg or get_settings()
    mcp, ctx = build_server(cfg)

    if cfg.metrics_enabled:
        metrics.start_metrics_server(9000)

    app = mcp.http_app(path="/mcp")
    app.add_middleware(BrowserMCPMiddleware, cfg=cfg, ctx=ctx)

    async def not_found(request: Request, _exc: Exception) -> HTMLResponse | JSONResponse:
        if "text/html" in request.headers.get("accept", ""):
            return HTMLResponse(not_found_page(), status_code=404)
        return JSONResponse({"error": "Not found"}, status_code=404)

    app.add_exception_handler(404, not_found)

    # Compose our index startup with FastMCP's own (session manager) lifespan.
    fastmcp_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def combined(scope_app):  # noqa: ANN001
        async with fastmcp_lifespan(scope_app):
            await _startup_index(ctx)
            yield

    app.router.lifespan_context = combined

    return app
