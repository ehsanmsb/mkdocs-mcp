# Configuration

Set `MKDOCS_MCP_SITES` to a JSON list containing at least one published MkDocs
site. Use the same setting for one site or many. Each entry needs a unique
lowercase `name` and an absolute HTTP(S) `base_url`. The optional
`search_index_url` points to a nonstandard index location; otherwise the server
fetches `<base_url>/search/search_index.json`.

```bash
export MKDOCS_MCP_SITES='[{"name":"docs","base_url":"https://docs.example.com"}]'
```

Add another object to the list to search more sites. Page IDs always include
the site name, for example `docs:guides/install`. The server keeps the last good
index for a site if a later refresh fails. Startup requires at least one site
to load.

All settings can be environment variables or entries in a local `.env` file.
Defaults match [`config.py`](../src/mkdocs_mcp/config.py).

| Variable | Default | Purpose |
| --- | --- | --- |
| `MKDOCS_MCP_SITES` | Required | JSON list of `{name, base_url, search_index_url?}` objects. Names must be unique lowercase slugs. |
| `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES` | `30` | How often to check for changed indexes. `0` disables periodic checks. |
| `MKDOCS_MCP_SERVER_NAME` | `MkDocs Docs` | Name shown to MCP clients and in the UI. |
| `MKDOCS_MCP_HOST` | `0.0.0.0` | HTTP listening interface. Use `127.0.0.1` for local-only access. |
| `MKDOCS_MCP_PORT` | `8000` | HTTP port; MCP endpoint is `/mcp`. |
| `MKDOCS_MCP_RATE_LIMIT_ENABLED` | `true` | Enables the request limiter; it is not authentication. |
| `MKDOCS_MCP_RATE_LIMIT_PER_SECOND` | `5.0` | Sustained request rate. |
| `MKDOCS_MCP_RATE_LIMIT_BURST` | `20` | Short burst capacity. |
| `MKDOCS_MCP_LOG_LEVEL` | `INFO` | Log detail; use `DEBUG` while diagnosing issues. |
| `MKDOCS_MCP_LOG_JSON` | `true` | Structured JSON logs; use `false` for readable local logs. |
| `MKDOCS_MCP_METRICS_ENABLED` | `true` | Prometheus metrics on port `9000`. |

`/health` and `/ready` are served on the HTTP port. `/ready` succeeds after at
least one index loads and reports degraded status if another site fails. MCP
clients connect without authentication, so control access at the network layer
if needed.

## Helm chart

The chart has one [`values.yaml`](../charts/mkdocs-mcp/values.yaml). Set
`config.sites` to one or more entries:

```yaml
config:
  sites:
    - name: docs
      base_url: https://docs.example.com
    - name: team
      base_url: https://team.example.com
      search_index_url: https://team.example.com/custom/search_index.json
```

The chart maps all application settings through its ConfigMap:

| Environment variable | Helm value |
| --- | --- |
| `MKDOCS_MCP_SITES` | `config.sites` (JSON encoded) |
| `MKDOCS_MCP_SERVER_NAME` | `config.serverName` |
| `MKDOCS_MCP_HOST` | `config.host` |
| `MKDOCS_MCP_PORT` | `config.port` |
| `MKDOCS_MCP_REINDEX_INTERVAL_MINUTES` | `config.reindexIntervalMinutes` |
| `MKDOCS_MCP_RATE_LIMIT_ENABLED` | `config.rateLimitEnabled` |
| `MKDOCS_MCP_RATE_LIMIT_PER_SECOND` | `config.rateLimitPerSecond` |
| `MKDOCS_MCP_RATE_LIMIT_BURST` | `config.rateLimitBurst` |
| `MKDOCS_MCP_LOG_LEVEL` | `config.logLevel` |
| `MKDOCS_MCP_LOG_JSON` | `config.logJson` |
| `MKDOCS_MCP_METRICS_ENABLED` | `config.metricsEnabled` |

Keep `config.host: 0.0.0.0` in Kubernetes so the Service can reach the pod.
Metrics are exposed on port `9000`. See [logs and metrics](OBSERVABILITY.md).
