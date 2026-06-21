"""Assemble the FastMCP app.

Cross-cutting concerns are handled by FastMCP's own building blocks:
  - authentication      -> StaticTokenVerifier (auth.build_verifier)
  - error handling      -> ErrorHandlingMiddleware
  - structured logging  -> StructuredLoggingMiddleware
  - timing              -> TimingMiddleware
  - rate limiting       -> RateLimitingMiddleware
  - metrics             -> PrometheusMiddleware (thin local glue)
  - health/ready routes -> mcp.custom_route
"""

from __future__ import annotations

import asyncio
import contextlib

from fastmcp import FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import StructuredLoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import build_verifier
from .config import Settings, get_settings
from .context import AppContext
from .obs import metrics
from .obs.logging import get_logger, setup_logging
from .obs.metrics import PrometheusMiddleware
from .tools import register_all

log = get_logger(__name__)


def build_server(cfg: Settings | None = None) -> tuple[FastMCP, AppContext]:
    cfg = cfg or get_settings()
    setup_logging(cfg.log_level, cfg.log_json)

    mcp = FastMCP(
        name=cfg.server_name,
        instructions=cfg.server_instructions,
        auth=build_verifier(cfg),
    )

    mcp.add_middleware(ErrorHandlingMiddleware())
    mcp.add_middleware(StructuredLoggingMiddleware())
    mcp.add_middleware(TimingMiddleware())
    if cfg.metrics_enabled:
        mcp.add_middleware(PrometheusMiddleware())
    if cfg.rate_limit_enabled:
        mcp.add_middleware(
            RateLimitingMiddleware(
                max_requests_per_second=cfg.rate_limit_per_second,
                burst_capacity=cfg.rate_limit_burst,
            )
        )

    ctx = AppContext(cfg)
    register_all(mcp, ctx)

    @mcp.custom_route("/health", methods=["GET"])
    @mcp.custom_route("/livez", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/ready", methods=["GET"])
    @mcp.custom_route("/readyz", methods=["GET"])
    async def ready(_request: Request) -> JSONResponse:
        loaded = ctx.store.is_loaded
        return JSONResponse(
            {"status": "ok" if loaded else "starting", "index_loaded": loaded},
            status_code=200 if loaded else 503,
        )

    return mcp, ctx


async def _startup_index(ctx: AppContext) -> None:
    warmed = await ctx.indexer.warm_load()
    if warmed:
        # Refresh in the background so we serve immediately from the snapshot.
        asyncio.create_task(ctx.indexer.safe_build())
    else:
        await ctx.indexer.safe_build()
    ctx.indexer.start_scheduler()


def create_app(cfg: Settings | None = None):
    """Return the ASGI app for streamable-http (uvicorn / gunicorn entrypoint)."""
    cfg = cfg or get_settings()
    mcp, ctx = build_server(cfg)

    if cfg.metrics_enabled:
        with contextlib.suppress(Exception):
            metrics.start_metrics_server(cfg.metrics_port)

    app = mcp.http_app(path=cfg.mcp_path)

    # Compose our index startup with FastMCP's own (session manager) lifespan.
    fastmcp_lifespan = app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def combined(scope_app):  # noqa: ANN001
        async with fastmcp_lifespan(scope_app):
            await _startup_index(ctx)
            yield

    app.router.lifespan_context = combined

    log.info("server_built", source=cfg.source_mode, auth=cfg.auth_mode, mcp_path=cfg.mcp_path)
    return app
