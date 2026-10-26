# Deploying the MkDocs MCP server on OKD / OpenShift

A generic, configurable MCP server for any MkDocs documentation site. All
site-specific values (URLs, tenants, topics) are supplied via Helm values
/ env — nothing is hardcoded.

## Prerequisites
- An OKD/OpenShift project (namespace).
- The image pushed to your registry (see root `Dockerfile` / `.github/workflows/release.yml`,
  which publishes to `ghcr.io/<owner>/<repo>`).
- Prometheus Operator if you want the `ServiceMonitor`.

## 1. Configure the documentation source
Copy `values-production.yaml` to `values-production.local.yaml` and set
`config.baseUrl`, `config.searchIndexUrl`, and `route.host` there. The local
file is ignored by Git. The checked-in values are examples and must not
contain private deployment addresses. MCP clients do not need a token. The
pod must be able to fetch the published search index over HTTPS.

## 2. Install / upgrade
The chart in this checkout defaults to the moving `main` image. Pin
`image.tag=sha-<commit>` for a repeatable deployment, as shown below. A
versioned chart attached to a GitHub release defaults to its matching image tag.

```bash
helm upgrade --install mkdocs-mcp charts/mkdocs-mcp \
  -n docs-mcp-staging --create-namespace \
  -f charts/mkdocs-mcp/values-staging.yaml \
  --set image.tag=sha-$(git rev-parse HEAD) \
  --set config.searchIndexUrl=https://docs.example.com/search/search_index.json \
  --set config.baseUrl=https://docs.example.com

helm upgrade --install mkdocs-mcp charts/mkdocs-mcp \
  -n docs-mcp --create-namespace \
  -f charts/mkdocs-mcp/values-production.local.yaml \
  --set image.tag=sha-$(git rev-parse HEAD)
```

## 3. Verify
```bash
oc -n docs-mcp rollout status deploy/mkdocs-mcp
oc -n docs-mcp get route mkdocs-mcp
curl -fsS https://<route-host>/health
curl -fsS https://<route-host>/ready
```

## 4. Connect a client
```json
{ "mcpServers": { "mkdocs-docs": {
  "type": "http",
  "url": "https://<route-host>/mcp" } } }
```

## Operational notes
- **Indexing**: each replica reads the published search index on startup and
  checks `ETag` or `Last-Modified` every `config.reindexIntervalMinutes`.
  No Git clone, Secret, or persistent volume is required.
- **Scaling/HA**: `replicaCount>=2`, pod anti-affinity, `PodDisruptionBudget`,
  optional HPA. Readiness gates traffic until the index is loaded.
- **Security**: non-root, read-only rootfs (writable `/tmp` only),
  dropped caps, `NetworkPolicy` limiting egress to DNS + HTTPS. OpenShift
  assigns the UID via SCC — do not set `runAsUser`.
- **Access**: anyone who can reach `/mcp` can use its read-only documentation
  tools. The server reads only the public MkDocs search index.
- **Topics**: customize the topic taxonomy with `MKDOCS_MCP_TOPICS_FILE`
  pointing at a mounted YAML, and pick the convenience aliases via
  `MKDOCS_MCP_FEATURED_TOPICS`.

## Troubleshooting
| Symptom | Check |
|---|---|
| Pod not ready | `oc logs` — search index URL or HTTPS egress failing? |
| Empty results | Check the published `search_index.json` and `get_statistics` |
| Wrong links | `MKDOCS_MCP_BASE_URL` does not match the published site |
