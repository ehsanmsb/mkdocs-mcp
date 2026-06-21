"""Entrypoint: run the MkDocs documentation MCP server over streamable-http."""

from __future__ import annotations

import uvicorn

from .config import get_settings
from .server import create_app


def run() -> None:
    cfg = get_settings()
    app = create_app(cfg)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_config=None)


if __name__ == "__main__":
    run()
