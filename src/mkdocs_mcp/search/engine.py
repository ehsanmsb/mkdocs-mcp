"""BM25 search over published MkDocs sections."""

from __future__ import annotations

from dataclasses import dataclass

from ..indexing.store import IndexStore
from ..indexing.text import make_snippet
from ..models import SearchHit
from ..obs import metrics
from .bm25 import BM25Index, tokenize


@dataclass
class Filters:
    doc_type: str | None = None
    page_id: str | None = None


class SearchEngine:
    def __init__(self) -> None:
        self.store = IndexStore()
        self.bm25 = BM25Index()

    def attach(self, store: IndexStore) -> None:
        """Swap in a freshly built corpus and keyword index."""
        bm25 = BM25Index()
        bm25.build([(f"{s.page_title} {s.heading}", s.text) for s in store.sections])
        self.store = store
        self.bm25 = bm25
        metrics.INDEX_PAGES.set(len(store.documents))
        metrics.INDEX_SECTIONS.set(len(store.sections))

    def search(
        self,
        query: str,
        filters: Filters | None = None,
        limit: int = 10,
        dedupe_pages: bool = True,
    ) -> list[SearchHit]:
        if limit <= 0:
            return []
        filters = filters or Filters()
        candidates = [
            i
            for i, section in enumerate(self.store.sections)
            if (not filters.doc_type or section.doc_type == filters.doc_type)
            and (not filters.page_id or section.page_id == filters.page_id)
        ]
        ranked = self.bm25.search(query, candidates)

        hits: list[SearchHit] = []
        seen_pages: set[str] = set()
        q_terms = tokenize(query)
        for i, score in ranked:
            sec = self.store.sections[i]
            if dedupe_pages and sec.page_id in seen_pages:
                continue
            seen_pages.add(sec.page_id)
            doc = self.store.get_doc(sec.page_id)
            breadcrumb = [sec.page_title]
            if sec.heading and sec.heading != sec.page_title:
                breadcrumb.append(sec.heading)
            snippet_text = sec.text
            if not snippet_text and doc:
                snippet_text = next(
                    (s.text for s in self.store.sections_of(sec.page_id) if s.text),
                    "",
                )
            hits.append(
                SearchHit(
                    page_id=sec.page_id,
                    title=sec.page_title,
                    heading=sec.heading,
                    breadcrumb=breadcrumb,
                    url=sec.url,
                    snippet=make_snippet(snippet_text, q_terms),
                    doc_type=sec.doc_type,
                    score=round(score, 4),
                )
            )
            if len(hits) >= limit:
                break
        metrics.SEARCHES.labels(result="hit" if hits else "miss").inc()
        return hits
