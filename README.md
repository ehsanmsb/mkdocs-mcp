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

Requires Python 3.12+ and `uv`. Python 3.14 is used for the Docker image.

```bash
uv sync --locked --python 3.14
source .venv/bin/activate
export MKDOCS_MCP_BASE_URL=https://docs.example.com
mkdocs-mcp
```

Replace the example URL with the public root of your MkDocs site. By default,
the server fetches `<base-url>/search/search_index.json` on startup and serves
MCP at `http://localhost:8000/mcp`. Set `MKDOCS_MCP_SEARCH_INDEX_URL` if your
site publishes its search index elsewhere. The index must be reachable when
the server starts.

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
- [Tools, search behavior, and limitations](docs/USAGE.md)
- [Deployment on OKD/OpenShift](charts/mkdocs-mcp/README.md)
- [Releases and versioning](docs/RELEASES.md)
- [Contributing and tests](docs/CONTRIBUTING.md)
