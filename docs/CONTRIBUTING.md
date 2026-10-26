# Contributing

Thanks for helping improve mkdocs-mcp. This guide keeps contributions predictable
for maintainers and easy to review.

## Development Setup

Use Python 3.12.

```bash
uv pip install -e '.[dev]'
```

For optional semantic or hybrid search work, install the vector extra:

```bash
uv pip install -e '.[dev,vectors]'
```

Run the server locally against a published MkDocs site:

```bash
export MKDOCS_MCP_BASE_URL=https://docs.example.com
export MKDOCS_MCP_SEARCH_INDEX_URL=https://docs.example.com/search/search_index.json

mkdocs-mcp
```

For parser development, set `MKDOCS_MCP_SOURCE_MODE=local` and
`MKDOCS_MCP_LOCAL_DIR` to a local MkDocs project directory.

## Validation

Before opening a pull request, run the checks that match your change:

```bash
ruff check src tests
ruff format --check src tests
pytest -q
helm lint charts/mkdocs-mcp
```

Use focused tests for small changes, and add broader tests when changing shared
indexing, parsing, search, or MCP tool behavior.

## Pull Requests

Keep pull requests scoped to one change. Include:

- a short summary of what changed
- the user-visible behavior or maintenance problem solved
- validation output, or a clear reason if a check was not run
- screenshots or command output when changing docs, chart behavior, or release workflows

Do not include secrets, private repository URLs, or
customer documentation content in issues, pull requests, tests, or fixtures.

## Commit Messages

Use Conventional Commits. Examples:

```text
feat: add search index source adapter
fix: handle pages without title metadata
feat!: rename source configuration variables
```

See [Releases and versioning](RELEASES.md) for version impact and image tags.

## Project Areas

Useful starting points:

- MCP server entrypoint: `src/mkdocs_mcp/server.py`
- CLI entrypoint: `src/mkdocs_mcp/main.py`
- Configuration: `src/mkdocs_mcp/config.py`
- Tools: `src/mkdocs_mcp/tools/`
- Indexing and parsing: `src/mkdocs_mcp/indexing/`
- Search: `src/mkdocs_mcp/search/`
- Source adapters: `src/mkdocs_mcp/sources/`
- Helm chart: `charts/mkdocs-mcp/`

## Issue Triage

Use the issue templates for bug reports, feature requests, and roadmap items.
For bugs, include a minimal configuration, reproduction steps, actual behavior,
expected behavior, logs, and the mkdocs-mcp version or image tag.
