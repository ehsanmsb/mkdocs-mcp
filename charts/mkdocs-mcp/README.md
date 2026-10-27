# Deploying MkDocs MCP on OKD / OpenShift

This chart uses one [`values.yaml`](values.yaml) for every deployment. Edit
`config.sites` to list one or more public MkDocs sites and set `route.host` to
your MCP hostname. Each site normally serves its index at
`<base_url>/search/search_index.json`; add `search_index_url` to an entry if its
index lives elsewhere. Replace the example addresses before deployment.

The pod needs DNS and HTTPS access to every configured site. MCP clients do not
need a token. A Prometheus Operator is needed only if `serviceMonitor.enabled`
is true.

## Install or upgrade

Pin `image.tag` to a built image version. For a checkout using the GitHub
workflow's commit image:

```bash
helm upgrade --install mkdocs-mcp charts/mkdocs-mcp \
  -n docs-mcp --create-namespace \
  --set image.tag=sha-$(git rev-parse HEAD)
```

The chart defaults to one replica, with CPU request/limit of 250m/500m and
memory request/limit of 512Mi/1Gi. It does not create an HPA, PDB, or
NetworkPolicy. Readiness gates traffic until a documentation index has loaded.
The container uses a non-root, read-only filesystem with writable `/tmp`.
OpenShift assigns the UID through its SCC.

## Verify

```bash
oc -n docs-mcp rollout status deploy/mkdocs-mcp
oc -n docs-mcp get route mkdocs-mcp
curl -fsS https://<route-host>/health
curl -fsS https://<route-host>/ready
```

Open `https://<route-host>/` for the UI. MCP clients connect to
`https://<route-host>/mcp`.

The server holds the published search indexes in memory and periodically checks
for changes using HTTP `ETag` or `Last-Modified` when available. No Git clone or
persistent volume is needed. Memory use grows with the combined index size of
the sites; monitor it before adding many large sites.

See [configuration](../../docs/CONFIGURATION.md) and
[observability](../../docs/OBSERVABILITY.md) for more detail.
