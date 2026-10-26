"""Configuration via environment variables / ConfigMap / Secret.

All settings are 12-factor and typed. Every env var is prefixed ``MKDOCS_MCP_``,
e.g. ``MKDOCS_MCP_BASE_URL=https://docs.example.com``.

The server is generic: no organization-, site-, or project-specific values are
hardcoded. Site-specific URLs and server identity are supplied here.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MKDOCS_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Server identity (surfaced to MCP clients) ---------------------
    server_name: str = "MkDocs Docs"

    # ---- Transport -----------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # ---- Source --------------------------------------------------------
    search_index_url: str = ""  # defaults to {base_url}/search/search_index.json

    # ---- Links ---------------------------------------------------------
    # Canonical base URL used to build deep-links returned to clients.
    base_url: str = "http://localhost:8000"

    # ---- Indexing ------------------------------------------------------
    reindex_interval_minutes: int = 30

    # ---- Rate limiting (FastMCP RateLimitingMiddleware) ----------------
    rate_limit_enabled: bool = True
    rate_limit_per_second: float = 5.0
    rate_limit_burst: int = 20

    # ---- Observability -------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True
    metrics_enabled: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
