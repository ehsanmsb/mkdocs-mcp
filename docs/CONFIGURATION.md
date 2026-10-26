# Configuration

The server reads the published MkDocs search index. Set the public site URL
with `MKDOCS_MCP_BASE_URL`; the index defaults to
`<base-url>/search/search_index.json`. All settings below can be passed as
environment variables or placed in a local `.env` file. Their defaults match
[`config.py`](../src/mkdocs_mcp/config.py).

| Variable | Default | When to set it |
| --- | --- | --- |
| `MKDOCS_MCP_BASE_URL` | `http://localhost:8000` | **Set for your site.** This is the documentation URL, used for links and the default search index URL. It is not the MCP server URL. |
| `MKDOCS_MCP_SEARCH_INDEX_URL` | empty | Only when the published index is at another URL. Empty uses `<base-url>/search/search_index.json`. |
| `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES` | `30` | Change how often the server checks for a new index. `0` disables periodic checks, but startup still loads it. HTTP `304` keeps the current index; refresh errors keep the last good index. |
| `MKDOCS_MCP_SERVER_NAME` | `MkDocs Docs` | Change the name shown to MCP clients. |
| `MKDOCS_MCP_HOST` | `0.0.0.0` | Change the listening interface; use `127.0.0.1` to allow local connections only. |
| `MKDOCS_MCP_PORT` | `8000` | Change the HTTP listening port. The MCP endpoint is `/mcp`. |
| `MKDOCS_MCP_RATE_LIMIT_ENABLED` | `true` | Turn the FastMCP request limiter on or off. This is not authentication. |
| `MKDOCS_MCP_RATE_LIMIT_PER_SECOND` | `5.0` | Change the sustained request rate. |
| `MKDOCS_MCP_RATE_LIMIT_BURST` | `20` | Change the short burst capacity. |
| `MKDOCS_MCP_LOG_LEVEL` | `INFO` | Change logging detail, for example to `DEBUG` while diagnosing an issue. |
| `MKDOCS_MCP_LOG_JSON` | `true` | Use structured JSON logs; set false for easier local reading. |
| `MKDOCS_MCP_METRICS_ENABLED` | `true` | Enable Prometheus metrics on port `9000`; disable if unused. |

The server exposes `/health` and `/ready` on its HTTP port. `/ready` succeeds
only after the index has loaded. MCP clients connect without authentication,
so control access through the network where you deploy it.

## Helm chart

The chart maps application settings from `config` in
[`values.yaml`](../charts/mkdocs-mcp/values.yaml) to environment variables.
Set `config.baseUrl` to the published site's root. Leave
`config.searchIndexUrl` empty for the standard MkDocs location; override it only
for a custom location. The chart fixes the application ports at `8000` and
`9000`, matching its container and Service configuration.
