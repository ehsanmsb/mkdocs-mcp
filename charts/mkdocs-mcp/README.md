# Deploying the MkDocs MCP server on OKD / OpenShift

A generic, configurable MCP server for any MkDocs documentation site. All
site-specific values (repo, URLs, tenants, topics) are supplied via Helm values
/ env — nothing is hardcoded.

## Prerequisites
- An OKD/OpenShift project (namespace).
- The image pushed to your registry (see root `Dockerfile` / `.github/workflows/ci.yml`,
  which publishes to `ghcr.io/<owner>/<repo>`).
- Prometheus Operator if you want the `ServiceMonitor`.

## 1. Create the auth secret (production)
Production uses an externally managed secret (`secrets.existingSecret`). Create
it with your platform's mechanism (Vault, ExternalSecrets) or manually:

```bash
oc -n docs-mcp create secret generic mkdocs-mcp-auth \
  --from-literal=MKDOCS_MCP_AUTH_MODE=bearer \
  --from-literal=MKDOCS_MCP_GIT_TOKEN=<repo-read-token> \
  --from-literal=MKDOCS_MCP_BEARER_TOKENS=<token1>,<token2> \
  --from-literal=MKDOCS_MCP_ADMIN_TOKENS=<admin-token>
```

For staging the chart can create the secret for you via `secrets.*` values.

## 2. Install / upgrade
```bash
helm upgrade --install mkdocs-mcp charts/mkdocs-mcp \
  -n docs-mcp-staging --create-namespace \
  -f charts/mkdocs-mcp/values-staging.yaml \
  --set image.tag=$(git rev-parse --short HEAD) \
  --set config.gitUrl=https://gitlab.example.com/org/docs.git \
  --set config.baseUrl=https://docs.example.com

helm upgrade --install mkdocs-mcp charts/mkdocs-mcp \
  -n docs-mcp --create-namespace \
  -f charts/mkdocs-mcp/values-production.yaml \
  --set image.tag=$(git rev-parse --short HEAD)
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
  "url": "https://<route-host>/mcp",
  "headers": { "Authorization": "Bearer <token>" } } } }
```

## Operational notes
- **Indexing**: each replica clones the docs repo and builds its index in
  seconds on startup, then refreshes every `config.reindexIntervalMinutes`.
- **Storage**: `persistence.enabled=false` (emptyDir) by default — correct for
  multi-replica Deployments. Only enable a PVC at `replicaCount=1` (RWO cannot
  be multi-mounted); for multi-replica warm caching use a StatefulSet or RWX.
- **Scaling/HA**: `replicaCount>=2`, pod anti-affinity, `PodDisruptionBudget`,
  optional HPA. Readiness gates traffic until the index is loaded.
- **Security**: non-root, read-only rootfs (writable `/data` + `/tmp` only),
  dropped caps, `NetworkPolicy` limiting egress to DNS + HTTPS. OpenShift
  assigns the UID via SCC — do not set `runAsUser`.
- **Auth**: static bearer tokens by default (FastMCP `StaticTokenVerifier`).
  Swap in JWT or an OAuth provider (Keycloak/GitHub/Google/…) by changing
  `auth.build_verifier` — no tool changes required.
- **Topics**: customize the topic taxonomy with `MKDOCS_MCP_TOPICS_FILE`
  pointing at a mounted YAML, and pick the convenience aliases via
  `MKDOCS_MCP_FEATURED_TOPICS`.

## Troubleshooting
| Symptom | Check |
|---|---|
| Pod not ready | `oc logs` — git clone failing? token / egress? |
| `401` from `/mcp` | token not in `MKDOCS_MCP_BEARER_TOKENS` |
| `rebuild_index` → permission error | token not in `MKDOCS_MCP_ADMIN_TOKENS` |
| Empty results | wrong `MKDOCS_MCP_MKDOCS_CONFIG` / branch; check `get_statistics` |
| Wrong links | `MKDOCS_MCP_BASE_URL` does not match the published site |
