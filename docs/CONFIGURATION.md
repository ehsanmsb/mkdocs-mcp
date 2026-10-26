# Configuration

All settings are environment variables with the `MKDOCS_MCP_` prefix. The
server also reads a local `.env` file. Values below are the defaults in
[`config.py`](../src/mkdocs_mcp/config.py). For a published site, set
`MKDOCS_MCP_BASE_URL`; the other settings are optional.

## Published site and transport

| Variable | Default | Meaning |
| --- | --- | --- |
| `MKDOCS_MCP_BASE_URL` | `http://localhost:8000` | Public root of the MkDocs site. Used to build the search index URL and page links. Set this to your actual site URL. |
| `MKDOCS_MCP_SEARCH_INDEX_URL` | empty | Full URL of the published `search_index.json`. When empty, the server uses `<base-url>/search/search_index.json`. |
| `MKDOCS_MCP_SOURCE_MODE` | `search_index` | `search_index` fetches the published index; `local` reads a local MkDocs project for development. |
| `MKDOCS_MCP_LOCAL_DIR` | `.` | MkDocs project directory when `SOURCE_MODE=local`. |
| `MKDOCS_MCP_DOCS_SUBDIR` | `docs` | Documentation directory inside `LOCAL_DIR`. |
| `MKDOCS_MCP_HOST` | `0.0.0.0` | Network interface on which the HTTP server listens. Set `127.0.0.1` to accept local connections only. |
| `MKDOCS_MCP_PORT` | `8000` | HTTP server port. |
| `MKDOCS_MCP_MCP_PATH` | `/mcp` | HTTP path for the MCP endpoint. |
| `MKDOCS_MCP_SERVER_NAME` | `MkDocs Docs` | Name shown to MCP clients. |
| `MKDOCS_MCP_SERVER_INSTRUCTIONS` | built-in guidance | Instructions shown to MCP clients about which tools to use. |

`MKDOCS_MCP_BASE_URL` is the documentation site, not the MCP server address.
Clients connect to the MCP server's host, port, and path. The MCP endpoint has
no client authentication, so access is controlled by where you expose it.

## Refresh and classification

| Variable | Default | Meaning |
| --- | --- | --- |
| `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES` | `30` | How often each server process checks the published index for changes. `0` disables periodic checks, but startup still loads it. If the server receives HTTP `304`, it keeps the current index; on a refresh error, it keeps the last good index. |
| `MKDOCS_MCP_TENANTS` | `[]` | JSON list of first path segments to label as tenants, for example `["team-a","team-b"]`. Empty means every first segment becomes a tenant. This affects labels and filters; it does not hide or exclude pages. |
| `MKDOCS_MCP_TOPICS_FILE` | unset | Path to a YAML topic taxonomy. When unset, the built-in vendor-neutral DevOps taxonomy is used. |
| `MKDOCS_MCP_FEATURED_TOPICS` | `["kubernetes","argocd","terraform","vault","gitlab"]` | JSON list of topics that get convenience tools such as `find_kubernetes_docs`. Each name must resolve in the topic taxonomy. |

A custom topic file can replace the built-in taxonomy:

```yaml
topics:
  payments:
    paths: ["/payments/"]
    keywords: ["checkout", "billing", "invoice"]
```

Set `MKDOCS_MCP_TOPICS_FILE=/path/to/topics.yml` to use it. For Helm
deployments, mount the file into the pod first.

## Search

| Variable | Default | Meaning |
| --- | --- | --- |
| `MKDOCS_MCP_BM25_K1` | `1.5` | BM25 term-frequency tuning. The default is suitable for normal use. |
| `MKDOCS_MCP_BM25_B` | `0.75` | BM25 document-length tuning. The default is suitable for normal use. |
| `MKDOCS_MCP_TITLE_BOOST` | `3` | How strongly page titles and headings are weighted relative to section text. |
| `MKDOCS_MCP_EMBEDDINGS_ENABLED` | `false` | Enables optional in-process vector search. Install `uv pip install -e '.[vectors]'` first; it adds a model and significant memory use. |
| `MKDOCS_MCP_EMBEDDINGS_MODEL` | `BAAI/bge-m3` | Sentence-transformers model used when embeddings are enabled. The model must be available to the server. |
| `MKDOCS_MCP_RRF_K` | `60` | Rank-fusion tuning when keyword and vector results are combined. |

Without embeddings, search uses BM25 keyword matching. For questions in a
different language from the documentation, the client should search using terms
in the documentation's language.

## Limits and observability

| Variable | Default | Meaning |
| --- | --- | --- |
| `MKDOCS_MCP_RATE_LIMIT_ENABLED` | `true` | Enables FastMCP's request rate limiter. This is not authentication. |
| `MKDOCS_MCP_RATE_LIMIT_PER_SECOND` | `5.0` | Sustained requests per second allowed by the limiter. |
| `MKDOCS_MCP_RATE_LIMIT_BURST` | `20` | Short burst capacity of the limiter. |
| `MKDOCS_MCP_LOG_LEVEL` | `INFO` | Application log level. |
| `MKDOCS_MCP_LOG_JSON` | `true` | Emit structured JSON logs when true. |
| `MKDOCS_MCP_METRICS_ENABLED` | `true` | Starts a Prometheus metrics endpoint. Set false if metrics are not needed. |
| `MKDOCS_MCP_METRICS_PORT` | `9000` | Port for the metrics endpoint when enabled. |

The server also exposes `/health` and `/ready` on its HTTP port. `/ready`
returns success only after the documentation index has loaded.
