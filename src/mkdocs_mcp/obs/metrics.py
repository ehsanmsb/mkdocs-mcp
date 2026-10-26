"""Low-cardinality Prometheus metrics and concise tool failure logs."""

from __future__ import annotations

import time

from fastmcp.server.middleware import Middleware, MiddlewareContext
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from .logging import get_logger

log = get_logger(__name__)

TOOL_CALLS = Counter("mkdocs_mcp_tool_calls_total", "MCP tool invocations.", ["tool", "status"])
TOOL_LATENCY = Histogram(
    "mkdocs_mcp_tool_latency_seconds",
    "MCP tool latency.",
    ["tool"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
INDEX_PAGES = Gauge("mkdocs_mcp_index_pages", "Indexed pages.")
INDEX_SECTIONS = Gauge("mkdocs_mcp_index_sections", "Indexed sections.")
INDEX_READY = Gauge("mkdocs_mcp_index_ready", "1 if an index is available, else 0.")
INDEX_LAST_CHECK = Gauge(
    "mkdocs_mcp_index_last_check_timestamp_seconds", "Last successful index check."
)
INDEX_LAST_BUILD = Gauge(
    "mkdocs_mcp_index_last_build_timestamp_seconds", "Last successful index rebuild."
)
INDEX_REFRESH = Counter("mkdocs_mcp_index_refresh_total", "Index refresh attempts.", ["result"])
INDEX_REFRESH_DURATION = Histogram(
    "mkdocs_mcp_index_refresh_duration_seconds",
    "Index fetch and rebuild duration.",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60),
)
SEARCHES = Counter("mkdocs_mcp_searches_total", "Searches by result.", ["result"])

_started = False


def start_metrics_server(port: int = 9000) -> None:
    global _started
    if not _started:
        start_http_server(port)
        _started = True


class ToolObservabilityMiddleware(Middleware):
    """Record tool metrics and log failures without request payloads."""

    def __init__(self, metrics_enabled: bool) -> None:
        self.metrics_enabled = metrics_enabled

    async def on_call_tool(self, context: MiddlewareContext, call_next):  # noqa: ANN001
        tool = getattr(context.message, "name", "unknown")
        start = time.perf_counter()
        status = "ok"
        try:
            return await call_next(context)
        except Exception as exc:
            status = "error"
            cause = exc.__cause__ or exc
            log.error(
                "tool_failed",
                tool=tool,
                error_type=type(cause).__name__,
                error=str(cause)[:240],
                duration_ms=round((time.perf_counter() - start) * 1000),
            )
            raise
        finally:
            if self.metrics_enabled:
                TOOL_LATENCY.labels(tool=tool).observe(time.perf_counter() - start)
                TOOL_CALLS.labels(tool=tool, status=status).inc()
