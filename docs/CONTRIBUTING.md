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

Run the server locally with a local MkDocs checkout:

```bash
export MKDOCS_MCP_SOURCE_MODE=local
export MKDOCS_MCP_REPO_DIR=/path/to/your/mkdocs-repo
export MKDOCS_MCP_MKDOCS_CONFIG=mkdocs.yml
export MKDOCS_MCP_BASE_URL=https://docs.example.com
export MKDOCS_MCP_AUTH_MODE=none

mkdocs-mcp
```

## Validation

Before opening a pull request, run the checks that match your change:

```bash
ruff check src tests
ruff format --check src tests
pytest -q
helm lint charts/mkdocs-mcp
```

Use focused tests for small changes, and add broader tests when changing shared
indexing, parsing, search, auth, or MCP tool behavior.

## Pull Requests

Keep pull requests scoped to one change. Include:

- a short summary of what changed
- the user-visible behavior or maintenance problem solved
- validation output, or a clear reason if a check was not run
- screenshots or command output when changing docs, chart behavior, or release workflows

Do not include secrets, private repository URLs, bearer tokens, cookies, or
customer documentation content in issues, pull requests, tests, or fixtures.

## Commit Messages

This repository uses Conventional Commits and semantic-release.

Common commit types:

- `feat:` for new user-facing capability
- `fix:` for bug fixes
- `perf:` for performance improvements
- `refactor:` for internal restructuring without a behavior change
- `docs:` for documentation-only changes
- `test:` for test-only changes
- `ci:` for workflow changes
- `chore:` for maintenance

Version impact:

- `feat:` creates a minor release
- `fix:` and `perf:` create a patch release
- `feat!:` or a `BREAKING CHANGE:` footer creates a major release
- `docs:`, `test:`, `ci:`, `chore:`, and `refactor:` do not create a release unless they include a breaking change

Examples:

```text
feat: add search index source adapter
fix: handle pages without title metadata
perf: reduce BM25 index rebuild allocations
ci: add semantic release workflow
feat!: rename authentication environment variables
```

## Release Flow

Merging conventional commits into `main` triggers the release workflow. When a
release is required, semantic-release calculates the next version, creates a
`vX.Y.Z` tag, builds Python and Helm package artifacts, publishes a GitHub
release, and pushes GHCR image tags.

Do not manually edit release tags for normal releases.

## Project Areas

Useful starting points:

- MCP server entrypoint: `src/mkdocs_mcp/server.py`
- CLI entrypoint: `src/mkdocs_mcp/main.py`
- Configuration: `src/mkdocs_mcp/config.py`
- Auth: `src/mkdocs_mcp/auth.py`
- Tools: `src/mkdocs_mcp/tools/`
- Indexing and parsing: `src/mkdocs_mcp/indexing/`
- Search: `src/mkdocs_mcp/search/`
- Source adapters: `src/mkdocs_mcp/sources/`
- Helm chart: `charts/mkdocs-mcp/`

## Issue Triage

Use the issue templates for bug reports, feature requests, and roadmap items.
For bugs, include a minimal configuration, reproduction steps, actual behavior,
expected behavior, logs, and the mkdocs-mcp version or image tag.
