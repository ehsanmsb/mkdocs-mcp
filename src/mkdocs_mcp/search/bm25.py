"""Lexical search via the ``rank-bm25`` library (BM25Okapi).

We only add the thin glue BM25 libraries leave to the caller:
  - tokenization (a trivial unicode-aware regex — heavyweight NLP tokenizers
    such as NLTK require downloadable data and are offline-hostile, so a regex
    is the appropriate, dependency-light choice here);
  - title/heading emphasis (by repeating title tokens in the indexed document,
    which BM25Okapi scores natively via term frequency).
"""
from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text) if len(t) > 1]


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75, title_boost: int = 3) -> None:
        self.k1 = k1
        self.b = b
        self.title_boost = max(1, title_boost)
        self._bm25: BM25Okapi | None = None
        self.n = 0

    def build(self, docs: list[tuple[str, str]]) -> None:
        """docs: list of (title_text, body_text), aligned with section order."""
        corpus = [tokenize(body) + tokenize(title) * self.title_boost for title, body in docs]
        self.n = len(corpus)
        # BM25Okapi requires a non-empty corpus.
        self._bm25 = BM25Okapi(corpus or [[""]], k1=self.k1, b=self.b)

    def search(self, query: str, candidates: list[int] | None = None) -> list[tuple[int, float]]:
        if self._bm25 is None or self.n == 0:
            return []
        q_terms = tokenize(query)
        if not q_terms:
            return []
        scores = self._bm25.get_scores(q_terms)
        pool = candidates if candidates is not None else range(self.n)
        ranked = [(i, float(scores[i])) for i in pool if scores[i] > 0]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
