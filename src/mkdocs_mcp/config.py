"""Configuration via environment variables / ConfigMap / Secret.

All settings are 12-factor and typed. Every env var is prefixed ``MKDOCS_MCP_``,
e.g. ``MKDOCS_MCP_SOURCE_MODE=git``.

The server is generic: no organization-, site-, or project-specific values are
hardcoded. Anything site-specific (URLs, repo, tenant segments, topic taxonomy,
server identity) is supplied here.
"""

from __future__ import annotations

from typing import Literal

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
    server_instructions: str = (
        "Search and explore the documentation. Start with search_docs for most "
        "questions; use find_by_topic for a whole technology; get_page to read a "
        "page; find_runbooks for operational runbooks; recent_changes for what "
        "changed recently."
    )

    # ---- Transport -----------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000
    mcp_path: str = "/mcp"

    # ---- Source --------------------------------------------------------
    # git           -> clone/pull a docs repo (rich metadata + git history)
    # search_index  -> fetch a published MkDocs search_index.json (zero deps)
    # local         -> read an already-checked-out docs dir (dev / tests)
    source_mode: Literal["git", "search_index", "local"] = "local"

    git_url: str = ""  # required when source_mode=git
    git_branch: str = "main"
    # Auth for private/internal repos. Leave token empty for public repos.
    # username: "oauth2" works for GitLab PATs; use your username or
    # "x-access-token" for GitHub PATs.
    git_token: str | None = None  # injected from a Secret
    git_username: str = "oauth2"
    repo_dir: str = "/data/repo"
    mkdocs_config: str = "mkdocs.yml"  # supplies the nav tree
    docs_subdir: str = "docs"

    # search_index source only:
    search_index_url: str = ""  # e.g. https://docs.example.com/search/search_index.json

    # ---- Links ---------------------------------------------------------
    # Canonical base URL used to build deep-links returned to clients.
    base_url: str = "http://localhost:8000"
    # Optional repo web URL for "edit this page" links.
    repo_web_url: str = ""
    edit_uri_template: str = "/-/edit/{branch}/{docs_subdir}/{rel_path}"
    edit_branch: str = "main"

    # ---- Classification (generic, fully configurable) ------------------
    # Top-level path segments treated as "tenants"/sections for filtering.
    # Empty list -> the first path segment is always treated as the tenant.
    tenants: list[str] = []
    # Optional path to a YAML topic taxonomy file. When unset, a vendor-neutral
    # default taxonomy of common DevOps tools is used (see indexing/metadata.py).
    topics_file: str | None = None
    # Topics that also get a dedicated find_<topic>_docs convenience tool.
    featured_topics: list[str] = [
        "kubernetes",
        "argocd",
        "terraform",
        "vault",
        "gitlab",
    ]

    # ---- Indexing ------------------------------------------------------
    reindex_interval_minutes: int = 30
    snapshot_path: str = "/data/index-snapshot.json"

    # ---- Search --------------------------------------------------------
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # How strongly title/heading terms outrank body terms (token repetition).
    title_boost: int = 3

    # Semantic / hybrid (optional; requires the `vectors` extra).
    embeddings_enabled: bool = False
    embeddings_model: str = "BAAI/bge-m3"  # multilingual, self-hosted
    rrf_k: int = 60  # Reciprocal Rank Fusion constant

    # ---- Auth ----------------------------------------------------------
    # none   -> open (local dev only)
    # bearer -> static bearer token(s) via FastMCP StaticTokenVerifier
    auth_mode: Literal["none", "bearer"] = "bearer"
    bearer_tokens: str = ""  # comma-separated; normal scope
    admin_tokens: str = ""  # comma-separated; admin scope (rebuild_index)

    # ---- Rate limiting (FastMCP RateLimitingMiddleware) ----------------
    rate_limit_enabled: bool = True
    rate_limit_per_second: float = 5.0
    rate_limit_burst: int = 20

    # ---- Observability -------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True
    metrics_enabled: bool = True
    metrics_port: int = 9000

    @property
    def bearer_token_set(self) -> set[str]:
        return {t.strip() for t in self.bearer_tokens.split(",") if t.strip()}

    @property
    def admin_token_set(self) -> set[str]:
        return {t.strip() for t in self.admin_tokens.split(",") if t.strip()}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
