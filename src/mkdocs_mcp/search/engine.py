"""Search engine: BM25 (rank-bm25) + optional semantic vectors, fused with RRF.

No result cache: at MkDocs scale BM25 scoring is sub-millisecond, and a cache
would risk serving stale hits after a reindex. If a corpus ever grows large
enough to need it, enable FastMCP's ResponseCachingMiddleware instead of adding
bespoke caching here.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..indexing.store import IndexStore
from ..indexing.text import make_snippet
from ..models import SearchHit
from ..obs import metrics
from .bm25 import BM25Index, tokenize
from .vectors import VectorIndex


@dataclass
class Filters:
    tenant: str | None = None
    doc_type: str | None = None
    topic: str | None = None
    runbook_only: bool = False


def _rrf(rankings: list[list[int]], k: int) -> dict[int, float]:
    """Reciprocal Rank Fusion across multiple ranked id lists."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return scores


class SearchEngine:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.store = IndexStore()
        self.bm25 = BM25Index(cfg.bm25_k1, cfg.bm25_b, cfg.title_boost)
        self.vectors = VectorIndex(cfg.embeddings_model)
        self.vocab: list[str] = []  # topic vocabulary for empty-state hints

    # ---- lifecycle -----------------------------------------------------
    def attach(self, store: IndexStore, vocab: list[str] | None = None) -> None:
        """Swap in a freshly built store and rebuild the search structures."""
        self.store = store
        if vocab is not None:
            self.vocab = vocab
        self.bm25.build([(f"{s.page_title} {s.heading}", s.text) for s in store.sections])
        if self.cfg.embeddings_enabled:
            self.vectors.build(
                [f"{s.page_title}\n{s.heading}\n{s.text}" for s in store.sections]
            )
        metrics.INDEX_PAGES.set(len(store.documents))
        metrics.INDEX_SECTIONS.set(len(store.sections))

    @property
    def vector_enabled(self) -> bool:
        return self.vectors.enabled

    # ---- filtering -----------------------------------------------------
    def _candidates(self, f: Filters) -> list[int] | None:
        if not (f.tenant or f.doc_type or f.topic or f.runbook_only):
            return None
        out: list[int] = []
        for i, s in enumerate(self.store.sections):
            if f.tenant and s.tenant != f.tenant:
                continue
            if f.doc_type and s.doc_type != f.doc_type:
                continue
            if f.topic and f.topic not in s.topics:
                continue
            if f.runbook_only and not s.is_runbook:
                continue
            out.append(i)
        return out

    # ---- search --------------------------------------------------------
    def search(
        self,
        query: str,
        filters: Filters | None = None,
        limit: int = 10,
        mode: str = "hybrid",
    ) -> list[SearchHit]:
        filters = filters or Filters()
        candidates = self._candidates(filters)
        bm25_scored = self.bm25.search(query, candidates)
        bm25_ranked = [i for i, _ in bm25_scored]
        scores = dict(bm25_scored)

        use_vec = mode in ("hybrid", "semantic") and self.vector_enabled
        if mode == "semantic" and use_vec:
            vec = self.vectors.search(query, top_k=100)
            if candidates is not None:
                cset = set(candidates)
                vec = [(i, s) for i, s in vec if i in cset]
            ranked = [i for i, _ in vec]
            scores = dict(vec)
        elif use_vec:
            vec_ranked = [i for i, _ in self.vectors.search(query, top_k=100)]
            if candidates is not None:
                cset = set(candidates)
                vec_ranked = [i for i in vec_ranked if i in cset]
            fused = _rrf([bm25_ranked, vec_ranked], self.cfg.rrf_k)
            ranked = [i for i, _ in sorted(fused.items(), key=lambda x: x[1], reverse=True)]
            scores = fused
        else:
            ranked = bm25_ranked

        # Deduplicate: at most one hit per page (best section wins).
        hits: list[SearchHit] = []
        seen_pages: set[str] = set()
        q_terms = tokenize(query)
        for i in ranked:
            sec = self.store.sections[i]
            if sec.page_id in seen_pages:
                continue
            seen_pages.add(sec.page_id)
            doc = self.store.get_doc(sec.page_id)
            breadcrumb = (doc.breadcrumb if doc else []) + [sec.page_title]
            if sec.heading and sec.heading != sec.page_title:
                breadcrumb = breadcrumb + [sec.heading]
            hits.append(
                SearchHit(
                    page_id=sec.page_id,
                    title=sec.page_title,
                    heading=sec.heading,
                    breadcrumb=breadcrumb,
                    url=sec.url,
                    snippet=make_snippet(sec.text, q_terms),
                    doc_type=sec.doc_type,
                    tenant=sec.tenant,
                    score=round(float(scores.get(i, 0.0)), 4),
                )
            )
            if len(hits) >= limit:
                break
        return hits

    # ---- related -------------------------------------------------------
    def related(self, page_id: str, limit: int = 5) -> list[SearchHit]:
        doc = self.store.get_doc(page_id)
        if not doc:
            return []
        seed = f"{doc.title} {' '.join(doc.headings)} {' '.join(doc.topics)}"
        hits = self.search(seed, Filters(), limit=limit + 3, mode="hybrid")
        return [h for h in hits if h.page_id != page_id][:limit]

    # ---- empty state ---------------------------------------------------
    def empty_state(self, query: str) -> list[SearchHit]:
        """No results -> suggest the nearest topics so the LLM can redirect."""
        q = query.lower()
        suggestions = [t for t in self.vocab if t in q] or self.vocab[:5]
        return [
            SearchHit(
                page_id="",
                title="No direct matches",
                heading="",
                breadcrumb=[],
                url="",
                snippet=(
                    "No pages matched. Try one of these documented topics via "
                    f"find_by_topic: {', '.join(suggestions)}."
                ),
                doc_type="reference",
                tenant=None,
                score=0.0,
            )
        ]
