# Tools and search behavior

| Task | Tools |
| --- | --- |
| Search | `search_docs`, `search_section` |
| Read pages | `get_page`, `get_section`, `list_pages` |
| Prepare a summary | `summarize_page` |
| Discover runbooks and code examples | `find_runbooks`, `find_examples` |
| Check status | `health_check`, `get_statistics` |

Start with `search_docs`, then pass a returned `page_id` to `get_page` or
`search_section`. Each result includes a link to the published page.
`summarize_page` supplies text and an outline to the MCP client; the server
itself does not run a language model.

Search uses BM25 keyword matching over sections in the published MkDocs
`search_index.json`. Page titles and headings get extra weight. No-match
queries return an empty list rather than a fabricated result. For questions in
another language, the client should search using terms from the documentation's
language.

The server checks the published index periodically using HTTP `ETag` or
`Last-Modified` when available. It holds the parsed corpus and search index in
process memory; each replica keeps its own copy. No Git clone, persistent
volume, or documentation pipeline job is required.

`get_page` returns text reconstructed from the search index and a link to the
rendered page. It cannot return the original Markdown, Git author, or Git
history. Pages excluded from the site's search index are also absent from the
MCP.
