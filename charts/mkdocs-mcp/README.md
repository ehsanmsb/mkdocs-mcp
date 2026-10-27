# MkDocs MCP Helm chart

Deploy one MCP endpoint that searches one or more public MkDocs sites. The chart
works on Kubernetes and OpenShift. It reads each site's published
`search/search_index.json`; it does not clone documentation repositories or
require client authentication.

## Requirements

- A Kubernetes cluster and Helm.
- A reachable MkDocs search index for every configured site. The pod needs DNS
  and outbound HTTP(S) access to those sites.
- An image registry accessible to the cluster. The default is
  `ghcr.io/ehsanmsb/mkdocs-mcp`.

The chart has one [values.yaml](values.yaml). Set `config.sites` to a list with
at least one entry. The example address in that file must be replaced. For one
site, use one item; for several sites, add more items. An item may set
`search_index_url` if its index is at a nonstandard location.

```yaml
config:
  sites:
    - name: docs
      base_url: https://docs.example.com
    - name: handbook
      base_url: https://handbook.example.com
      search_index_url: https://handbook.example.com/custom/search_index.json
```

## Kubernetes install

From a repository checkout, replace the example URL in this command:

```bash
helm upgrade --install mkdocs-mcp ./charts/mkdocs-mcp \
  --namespace docs-mcp --create-namespace \
  --set-json 'config.sites=[{"name":"docs","base_url":"https://docs.example.com"}]'
kubectl -n docs-mcp rollout status deployment/mkdocs-mcp
kubectl -n docs-mcp port-forward service/mkdocs-mcp 8000:8000
```

Open `http://localhost:8000/` for the status UI. Configure an MCP client with
`http://localhost:8000/mcp` while port forwarding.

For an external endpoint, enable the optional Ingress and set its hostname and
Ingress class. Set `ingress.tlsSecretName` when a TLS Secret terminates HTTPS at
the Ingress controller:

```bash
helm upgrade --install mkdocs-mcp ./charts/mkdocs-mcp \
  --namespace docs-mcp --create-namespace \
  --set-json 'config.sites=[{"name":"docs","base_url":"https://docs.example.com"}]' \
  --set ingress.enabled=true \
  --set ingress.host=mcp.example.com \
  --set ingress.className=nginx \
  --set ingress.tlsSecretName=mcp-tls
```

The Ingress routes `/`, `/mcp`, `/health`, and `/ready` to the HTTP Service.
TLS Secret creation and DNS records are managed outside this chart.

## OpenShift install

The same chart supports an OpenShift Route. Enable it instead of Ingress; omit
`route.host` to let OpenShift assign a hostname. The default Route TLS mode is
edge termination with HTTP-to-HTTPS redirect. OpenShift assigns the container
UID through its SCC; the chart does not pin `runAsUser`.

```bash
helm upgrade --install mkdocs-mcp ./charts/mkdocs-mcp \
  --namespace docs-mcp --create-namespace \
  --set-json 'config.sites=[{"name":"docs","base_url":"https://docs.example.com"}]' \
  --set route.enabled=true
oc -n docs-mcp rollout status deployment/mkdocs-mcp
oc -n docs-mcp get route mkdocs-mcp
```

Set `route.host` when you need a specific OpenShift hostname. Use the Route's
`https://<host>/mcp` URL in MCP clients.

## Defaults and optional resources

An empty `image.tag` uses the chart's `appVersion`; each release updates both
versions together. A versioned chart package is attached to each GitHub
release. Set `image.tag` explicitly only to deploy a different image.

| Setting | Default | Purpose |
| --- | --- | --- |
| `replicaCount` | `1` | Number of pods when HPA is disabled. |
| `resources.requests` | `250m` CPU, `512Mi` memory | Scheduler reservation. |
| `resources.limits` | `500m` CPU, `1Gi` memory | Maximum pod resources. |
| `route.enabled` | `false` | OpenShift Route; requires OpenShift. |
| `ingress.enabled` | `false` | Kubernetes Ingress; requires an Ingress controller. |
| `serviceMonitor.enabled` | `false` | Prometheus Operator ServiceMonitor. |
| `autoscaling.enabled` | `false` | Optional HPA. |
| `podDisruptionBudget.enabled` | `false` | Optional PDB. |
| `networkPolicy.enabled` | `false` | Optional ingress/egress policy. |

Metrics are served on port `9000` when `config.metricsEnabled` is true. Enable
`serviceMonitor.enabled` only when the Prometheus Operator CRD is installed.
The optional NetworkPolicy allows DNS and HTTPS egress; adapt it if a site uses
plain HTTP or your cluster's DNS requires different rules. The container runs
without root privileges, with a read-only filesystem and writable `/tmp`.

The server holds the published indexes in memory. Memory use grows with the
combined size of all configured sites. Check `/ready` after deployment and
monitor memory before adding many large sites. See
[configuration](../../docs/CONFIGURATION.md) and
[observability](../../docs/OBSERVABILITY.md) for all settings and metrics.
