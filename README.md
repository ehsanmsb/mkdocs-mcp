# MkDocs MCP Server

[![Build and Release](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml)
[![Release](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/ehsanmsb/mkdocs-mcp)](https://github.com/ehsanmsb/mkdocs-mcp/releases)
[![GHCR image](https://img.shields.io/badge/ghcr.io-mkdocs--mcp-blue)](https://github.com/ehsanmsb/mkdocs-mcp/pkgs/container/mkdocs-mcp)
[![License](https://img.shields.io/github/license/ehsanmsb/mkdocs-mcp)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-markdown-blue)](docs/)

A generic, configurable [Model Context Protocol](https://modelcontextprotocol.io)
server that makes **any [MkDocs](https://www.mkdocs.org/) documentation site
searchable and explorable** from MCP clients (Claude CLI, IDEs, …).

Nothing is organization- or project-specific: the published site URL, tenants,
topic taxonomy, and server identity are all supplied via configuration.

- **Transport:** streamable-http
- **Search:** BM25 (`rank-bm25`) with an optional self-hosted **semantic/hybrid**
  layer (`sentence-transformers`, fused with Reciprocal Rank Fusion)
- **Source of truth:** the published MkDocs `search/search_index.json`.
  The server does not clone the documentation repository.
- Built on established libraries — FastMCP (middleware, transport),
  `markdown-it-py` + `python-markdown` + `python-frontmatter` (parsing),
  `pydantic-settings`, `structlog`, `prometheus-client`.

---

## Quick start (local)

```bash
uv pip install -e .

export MKDOCS_MCP_BASE_URL=https://docs.example.com
export MKDOCS_MCP_SEARCH_INDEX_URL=https://docs.example.com/search/search_index.json

mkdocs-mcp        # serves http://0.0.0.0:8000/mcp
```

Health: `GET /health`, readiness: `GET /ready`, metrics: `:9000/metrics`.

## Production configuration

Copy `charts/mkdocs-mcp/values-production.yaml` to the Git-ignored
`charts/mkdocs-mcp/values-production.local.yaml`, then set the published
site URL, search index URL, and MCP hostname there. The search index must be
reachable by the pod. MCP clients connect without authentication.

## Connect from Claude CLI (HTTP)

```json
{
  "mcpServers": {
    "mkdocs-docs": {
      "type": "http",
      "url": "https://docs-mcp.example.com/mcp"
    }
  }
}
```

## Configuration

All settings are env vars prefixed `MKDOCS_MCP_` (see `src/mkdocs_mcp/config.py`).

| Var | Default | Notes |
|-----|---------|-------|
| `MKDOCS_MCP_SOURCE_MODE` | `search_index` | `search_index` \| `local` (development) |
| `MKDOCS_MCP_SEARCH_INDEX_URL` | `{base_url}/search/search_index.json` | published MkDocs search data |
| `MKDOCS_MCP_BASE_URL` | `http://localhost:8000` | used for deep-links |
| `MKDOCS_MCP_TENANTS` | `[]` | restrict tenant segments (else first path segment) |
| `MKDOCS_MCP_TOPICS_FILE` | — | YAML topic taxonomy (else vendor-neutral default) |
| `MKDOCS_MCP_FEATURED_TOPICS` | k8s/argocd/terraform/vault/gitlab | topics that get a `find_<topic>_docs` alias |
| `MKDOCS_MCP_EMBEDDINGS_ENABLED` | `false` | needs the `vectors` extra |
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
**Navigation:** `get_page`, `get_section`, `list_pages`
**Knowledge:** `summarize_page`, `related_documents`, `suggest_reading`
**Discovery:** `find_runbooks`, `find_examples`
**Topics:** `find_by_topic` (+ `find_<topic>_docs` aliases generated from `FEATURED_TOPICS`)
**Status:** `health_check`, `get_statistics`

The MCP endpoint is open to clients that can reach it. On startup the server
loads the published search index. Every `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES`
it checks for changes using HTTP `ETag` or `Last-Modified`; unchanged content
is not rebuilt. On a refresh error the last good in-memory index remains
available. A restart requires the published index to be reachable.

`get_page` returns the content available in MkDocs search data and a link to
the rendered page. It does not return the original Markdown source or Git
author/change history. Pages omitted from the site's search index are omitted
from the MCP as well.

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

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for development setup,
validation, pull request expectations, and commit message rules.

## Releases

This repository uses Semantic Versioning with `semantic-release` and
Conventional Commits.

When a branch is merged into `main`, the release workflow analyzes the commits
since the previous release, calculates the next version, creates the Git tag
automatically, builds Python and Helm package artifacts, publishes a GitHub
release with generated release notes, and pushes a GHCR image. The tag starts
with `v` (for example, `v1.2.3`).

Every successful push to `main` publishes `main` and `sha-<commit-sha>` image
tags. A `feat:`, `fix:`, or `perf:` commit also creates a semantic version,
GitHub release, and versioned Python and Helm artifacts. Semantic release
tags the same tested image as follows:

- `<version>` such as `1.2.3`
- `<major>.<minor>` such as `1.2`
- `latest`

Release notes are grouped into:

- `Features`
- `Bug Fixes`
- `Performance`
- `Refactoring`

Low-signal commit types such as `docs:`, `test:`, `chore:`, `ci:`, and
`build:` are hidden from published release notes unless they include a breaking
change.

Use standard Conventional Commit syntax:

- `feat: add source adapter` -> minor release
- `fix: handle empty search index` -> patch release
- `perf: reduce indexing allocations` -> patch release
- `refactor: split parser metadata handling` -> no version bump, but shown in release notes
- `feat!: change configuration names` -> major release
- `BREAKING CHANGE: configuration names changed` in the commit footer -> major release

## Deployment

Container + Helm chart for OKD/OpenShift live in `charts/mkdocs-mcp/`.
See [charts/mkdocs-mcp/README.md](charts/mkdocs-mcp/README.md).
