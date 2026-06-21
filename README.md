# MkDocs MCP Server

A generic, configurable [Model Context Protocol](https://modelcontextprotocol.io)
server that makes **any [MkDocs](https://www.mkdocs.org/) documentation site
searchable and explorable** from MCP clients (Claude CLI, IDEs, …).

Nothing is organization- or project-specific: the docs repo, URLs, tenants,
topic taxonomy, and server identity are all supplied via configuration.

- **Transport:** streamable-http
- **Search:** BM25 (`rank-bm25`) with an optional self-hosted **semantic/hybrid**
  layer (`sentence-transformers`, fused with Reciprocal Rank Fusion)
- **Source of truth:** the docs **git repo** (with a `search_index.json` and a
  `local` fallback)
- Built on established libraries — FastMCP (auth, middleware, transport),
  `markdown-it-py` + `python-markdown` + `python-frontmatter` (parsing),
  `pydantic-settings`, `structlog`, `prometheus-client`.

---

## Quick start (local)

```bash
uv pip install -e .

export MKDOCS_MCP_SOURCE_MODE=local
export MKDOCS_MCP_REPO_DIR=/path/to/your/mkdocs-repo
export MKDOCS_MCP_MKDOCS_CONFIG=mkdocs.yml
export MKDOCS_MCP_BASE_URL=https://docs.example.com
export MKDOCS_MCP_AUTH_MODE=none

mkdocs-mcp        # serves http://0.0.0.0:8000/mcp
```

Health: `GET /health`, readiness: `GET /ready`, metrics: `:9000/metrics`.

## Connect from Claude CLI (HTTP)

```json
{
  "mcpServers": {
    "mkdocs-docs": {
      "type": "http",
      "url": "https://mkdocs-mcp.example.com/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

## Configuration

All settings are env vars prefixed `MKDOCS_MCP_` (see `src/mkdocs_mcp/config.py`).

| Var | Default | Notes |
|-----|---------|-------|
| `MKDOCS_MCP_SOURCE_MODE` | `local` | `git` \| `search_index` \| `local` |
| `MKDOCS_MCP_GIT_URL` | — | docs repo to clone (when `git`) |
| `MKDOCS_MCP_MKDOCS_CONFIG` | `mkdocs.yml` | supplies the nav tree |
| `MKDOCS_MCP_BASE_URL` | `http://localhost:8000` | used for deep-links |
| `MKDOCS_MCP_TENANTS` | `[]` | restrict tenant segments (else first path segment) |
| `MKDOCS_MCP_TOPICS_FILE` | — | YAML topic taxonomy (else vendor-neutral default) |
| `MKDOCS_MCP_FEATURED_TOPICS` | k8s/argocd/terraform/vault/gitlab | topics that get a `find_<topic>_docs` alias |
| `MKDOCS_MCP_EMBEDDINGS_ENABLED` | `false` | needs the `vectors` extra |
| `MKDOCS_MCP_AUTH_MODE` | `bearer` | `none` \| `bearer` |
| `MKDOCS_MCP_BEARER_TOKENS` / `_ADMIN_TOKENS` | — | comma-separated |
| `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES` | `30` | `0` disables |

### Custom topic taxonomy

```yaml
# topics.yml  (MKDOCS_MCP_TOPICS_FILE=/path/topics.yml)
topics:
  payments:
    paths: ["/payments/"]
    keywords: ["checkout", "billing", "invoice"]
```

## Tools

**Search:** `search_docs`, `search_section`, `semantic_search`
**Navigation:** `get_page`, `get_section`, `list_categories`, `list_pages`, `browse_tree`
**Knowledge:** `summarize_page`, `related_documents`, `suggest_reading`
**Discovery:** `recent_changes`, `find_runbooks`, `find_examples`
**Topics:** `find_by_topic` (+ `find_<topic>_docs` aliases generated from `FEATURED_TOPICS`)
**Admin:** `rebuild_index` (admin scope), `health_check`, `get_statistics`

## Auth

Static bearer tokens are verified by FastMCP's `StaticTokenVerifier`; admin
tokens carry the `admin` scope, required by `rebuild_index`. To use JWT or an
OAuth provider (Keycloak, GitHub, Google, …), change `build_verifier` in
`src/mkdocs_mcp/auth.py` to the matching FastMCP provider — the tools are
unaffected.

## Semantic / hybrid search (optional)

```bash
uv pip install -e '.[vectors]'
export MKDOCS_MCP_EMBEDDINGS_ENABLED=true
export MKDOCS_MCP_EMBEDDINGS_MODEL=BAAI/bge-m3   # multilingual, self-hosted
```

Embeddings run in-process; no external embedding API is used.

## Tests

```bash
uv pip install -e '.[dev]'
pytest
ruff check src tests
```

## Deployment

Container + Helm chart for OKD/OpenShift live in `charts/mkdocs-mcp/`.
See [charts/mkdocs-mcp/README.md](charts/mkdocs-mcp/README.md).
