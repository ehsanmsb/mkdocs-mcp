# Logs and metrics

The server writes short JSON logs to stdout by default. Normal MCP calls and
HTTP health probes do not produce access logs; Prometheus records tool calls
and index checks. Set `config.logLevel: DEBUG` temporarily to see unchanged
index checks.

| Event | Level | Useful fields |
| --- | --- | --- |
| `index_updated` | INFO | `pages`, `sections`, `sites_loaded`, `sites_failed`, `duration_ms` |
| `site_refresh_failed` | ERROR | `site`, `error_type`, `error` |
| `index_refresh_failed` | ERROR | `error_type`, `error`, `retained_pages` |
| `tool_failed` | ERROR | `tool`, `error_type`, `error`, `duration_ms` |

An index refresh failure keeps the last good content for that site. The server
can start when at least one configured site loads; `health_check` reports
`loaded_sites` and `failed_sites`, and returns `degraded` while a source is
failing. If every site fails at startup, the pod cannot become ready. Error
messages are capped at 240 characters.
The middleware does not log request payloads, though an exception message can
contain input supplied by a caller.

## Prometheus

With `config.metricsEnabled: true`, each pod exposes `/metrics` on port `9000`.
The Helm chart creates a `ServiceMonitor` when both `serviceMonitor.enabled`
and `config.metricsEnabled` are true. Tool names and fixed result values are the
only application labels; queries, URLs, and page IDs are never metric labels.

| Metric | Use |
| --- | --- |
| `mkdocs_mcp_tool_calls_total{tool,status}` | Tool volume and failures (`ok` or `error`). |
| `mkdocs_mcp_tool_latency_seconds` | Tool latency histogram. |
| `mkdocs_mcp_searches_total{result}` | Search hit or miss rate. |
| `mkdocs_mcp_index_refresh_total{result}` | Index checks (`updated`, `unchanged`, `error`). |
| `mkdocs_mcp_index_refresh_duration_seconds` | Index fetch and rebuild latency. |
| `mkdocs_mcp_index_ready` | `1` when a usable index is loaded. |
| `mkdocs_mcp_index_pages`, `mkdocs_mcp_index_sections` | Current corpus size. |
| `mkdocs_mcp_index_last_check_timestamp_seconds` | Last successful check, including HTTP 304. |
| `mkdocs_mcp_index_last_build_timestamp_seconds` | Last successful content rebuild. |

Useful Grafana panels and alert expressions:

```promql
# Tool errors per second, grouped by tool
sum by (tool) (rate(mkdocs_mcp_tool_calls_total{status="error"}[5m]))

# 95th percentile tool latency, grouped by tool
histogram_quantile(0.95, sum by (le, tool) (rate(mkdocs_mcp_tool_latency_seconds_bucket[5m])))

# Share of searches with no result
sum(rate(mkdocs_mcp_searches_total{result="miss"}[5m]))
/
clamp_min(sum(rate(mkdocs_mcp_searches_total[5m])), 0.001)

# Alert after three failed refresh attempts in fifteen minutes
increase(mkdocs_mcp_index_refresh_total{result="error"}[15m]) >= 3

# Alert when a pod has not checked its index for an hour
time() - mkdocs_mcp_index_last_check_timestamp_seconds > 3600

# Alert when a pod has no usable index
mkdocs_mcp_index_ready == 0
```

Choose the stale-check threshold relative to `config.reindexIntervalMinutes`.
Use Prometheus `up` as a separate alert for an unreachable metrics endpoint.
