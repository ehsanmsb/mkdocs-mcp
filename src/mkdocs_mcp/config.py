"""Configuration via environment variables / ConfigMap / Secret.

All settings are 12-factor and typed. Every env var is prefixed ``MKDOCS_MCP_``,
e.g. ``MKDOCS_MCP_BASE_URL=https://docs.example.com``.

The server is generic: no organization-, site-, or project-specific values are
hardcoded. Site-specific URLs and server identity are supplied here.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import BaseModel, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SiteConfig(BaseModel):
    name: str
    base_url: str
    search_index_url: str = ""

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
            raise ValueError("Site name must use lowercase letters, numbers, '-' or '_'")
        return value

    @field_validator("base_url", "search_index_url")
    @classmethod
    def valid_url(cls, value: str, info: ValidationInfo) -> str:
        if not value and info.field_name == "base_url":
            raise ValueError("Site base_url is required")
        if value:
            parts = urlsplit(value)
            if parts.scheme not in {"http", "https"} or not parts.netloc:
                raise ValueError("Site URL must be an absolute HTTP(S) URL")
            if info.field_name == "base_url" and (parts.query or parts.fragment):
                raise ValueError("Site base_url must not contain a query or fragment")
        return value


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
    sites: list[SiteConfig] = []  # JSON list; empty keeps the single-site settings above

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

    @model_validator(mode="after")
    def unique_sites(self) -> Settings:
        names = [site.name for site in self.sites]
        if len(names) != len(set(names)):
            raise ValueError("Site names must be unique")
        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
