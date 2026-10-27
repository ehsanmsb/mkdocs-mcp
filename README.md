![MkDocs MCP banner](assets/mkdocs-mcp-banner.jpg)

# MkDocs MCP Server

[![Build and Release](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml/badge.svg)](https://github.com/ehsanmsb/mkdocs-mcp/actions/workflows/release.yml)
[![Latest release](https://img.shields.io/github/v/release/ehsanmsb/mkdocs-mcp)](https://github.com/ehsanmsb/mkdocs-mcp/releases)
[![License](https://img.shields.io/github/license/ehsanmsb/mkdocs-mcp)](LICENSE)

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server for
public [MkDocs](https://www.mkdocs.org/) sites that publish a search index. It
searches the published `search/search_index.json` and returns relevant
sections, page text, and links over HTTP. It does not clone the documentation
repository or require MCP client authentication.

## Quick start

Requires Python 3.14 and `uv`.

```bash
uv sync --locked --python 3.14
source .venv/bin/activate
export MKDOCS_MCP_SITES='[{"name":"docs","base_url":"https://docs.example.com"}]'
mkdocs-mcp
```

Replace the example URL with the public root of your MkDocs site. The server
fetches `<base_url>/search/search_index.json` on startup and serves MCP at
`http://localhost:8000/mcp`. If the index is elsewhere, add `search_index_url`
to that site's object. The index must be reachable when the server starts.

Opening `/` in a browser shows the server status and MCP connection URL.
Opening `/mcp` in a browser shows the same page; MCP clients continue to use
`/mcp` for protocol requests.

To search several sites through the same endpoint, add more entries to
`MKDOCS_MCP_SITES`. Search results identify their site and link to the original
pages:

```bash
export MKDOCS_MCP_SITES='[{"name":"atlas","base_url":"https://atlas.example.com"},{"name":"team","base_url":"https://team.example.com"}]'
```

The server searches all configured sites with one BM25 index. A site that
fails to refresh keeps its last good content; other sites remain searchable.

For MCP clients that use an `mcpServers` JSON configuration:

```json
{
  "mcpServers": {
    "mkdocs-docs": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Documentation

- [Configuration and environment variables](docs/CONFIGURATION.md)
- [Logs, metrics, dashboards, and alerts](docs/OBSERVABILITY.md)
- [Tools, search behavior, and limitations](docs/USAGE.md)
- [Deployment on OKD/OpenShift](charts/mkdocs-mcp/README.md)
- [Releases and versioning](docs/RELEASES.md)
- [Contributing and tests](docs/CONTRIBUTING.md)
