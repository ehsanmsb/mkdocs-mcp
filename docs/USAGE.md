# Tools and search behavior

| Task | Tools |
| --- | --- |
| Search | `search_docs`, `search_section`, `semantic_search` |
| Read pages | `get_page`, `get_section`, `list_pages` |
| Prepare a summary or find related pages | `summarize_page`, `related_documents`, `suggest_reading` |
| Discover runbooks and examples | `find_runbooks`, `find_examples` |
| Browse topics | `find_by_topic`, plus configured `find_<topic>_docs` aliases |
| Check status | `health_check`, `get_statistics` |

Start with `search_docs`, then pass a returned `page_id` to `get_page` or
`search_section`. `summarize_page` supplies page text and an outline to the MCP
client; the server itself does not run a language model.

The published MkDocs search index is the source of truth. The server checks it
periodically using HTTP `ETag` or `Last-Modified` when available. It holds the
parsed corpus and BM25 index in process memory. Each replica keeps its own
copy; no Git clone, persistent volume, or separate Atlas pipeline job is
required.

`get_page` returns text reconstructed from the search index and a link to the
rendered page. It cannot return the original Markdown, Git author, or Git
history. A page omitted from the site's search index is also absent from the
MCP. Content that MkDocs excludes from search is unavailable to these tools.

Search uses keyword matching by default. Optional vector search is described
in [Configuration](CONFIGURATION.md#search).
