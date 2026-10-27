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

`search_docs` ranks all configured sites in one corpus.
Each hit includes its site name and a page ID such as `atlas:guides/install`.
Pass that ID to `get_page` or `search_section`; use the optional `site` filter
to search only one site. `health_check` lists sites that failed their latest
refresh, and `get_statistics.by_site` reports page counts. The last good
content from a failed site remains searchable. Broad queries can mix results
from several sites; set `site` when the intended documentation is known.

Search uses BM25 keyword matching over sections in the published MkDocs
`search_index.json`. Page titles and headings get extra weight. No-match
queries return an empty list rather than a fabricated result. For questions in
another language, the client should search using terms from the documentation's
language.

The server checks the published index periodically using HTTP `ETag` or
`Last-Modified` when available. It holds the parsed corpus and search index in
process memory; each replica keeps its own copy. Memory use grows with the
combined size of the configured sites. No Git clone, persistent
volume, or documentation pipeline job is required.

`get_page` returns text reconstructed from the search index and a link to the
rendered page. It cannot return the original Markdown, Git author, or Git
history. Pages excluded from the site's search index are also absent from the
MCP.
