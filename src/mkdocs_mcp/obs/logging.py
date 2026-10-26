"""Structured logging (JSON to stdout for OKD log collection)."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.typing import Processor


def _skip_duplicate_tool_error(record: logging.LogRecord) -> bool:
    return not record.getMessage().startswith(("Error calling tool", "Invalid arguments for tool"))


def setup_logging(level: str = "INFO", json: bool = True) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    for name in ("fastmcp", "mcp", "httpx", "httpcore", "uvicorn"):
        logging.getLogger(name).setLevel(logging.WARNING)
    fastmcp_tools = logging.getLogger("fastmcp.server.server")
    if _skip_duplicate_tool_error not in fastmcp_tools.filters:
        fastmcp_tools.addFilter(_skip_duplicate_tool_error)
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "mkdocs_mcp") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
