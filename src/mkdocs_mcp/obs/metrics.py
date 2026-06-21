"""Prometheus metrics + a FastMCP middleware that records per-tool metrics.

prometheus-client provides the registry/exposition; FastMCP provides the
middleware hook. The only glue is this small middleware (FastMCP ships timing
and logging middleware but no Prometheus integration).
"""
from __future__ import annotations

import time

from fastmcp.server.middleware import Middleware, MiddlewareContext
from prometheus_client import Counter, Gauge, Histogram, start_http_server

TOOL_CALLS = Counter(
    "mkdocs_mcp_tool_calls_total", "MCP tool invocations.", ["tool", "status"]
)
TOOL_LATENCY = Histogram(
    "mkdocs_mcp_tool_latency_seconds",
    "MCP tool latency.",
    ["tool"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
INDEX_PAGES = Gauge("mkdocs_mcp_index_pages", "Indexed pages.")
INDEX_SECTIONS = Gauge("mkdocs_mcp_index_sections", "Indexed sections.")
INDEX_AGE = Gauge("mkdocs_mcp_index_age_seconds", "Seconds since last index build.")
REINDEX = Counter("mkdocs_mcp_reindex_total", "Re-index runs.", ["status"])

_started = False


def start_metrics_server(port: int = 9000) -> None:
    global _started
    if not _started:
        start_http_server(port)
        _started = True


class PrometheusMiddleware(Middleware):
    """Records call count + latency for every tool call."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):  # noqa: ANN001
        tool = getattr(context.message, "name", "unknown")
        start = time.perf_counter()
        status = "ok"
        try:
            return await call_next(context)
        except Exception:
            status = "error"
            raise
        finally:
            TOOL_LATENCY.labels(tool=tool).observe(time.perf_counter() - start)
            TOOL_CALLS.labels(tool=tool, status=status).inc()
