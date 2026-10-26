"""In-memory documentation corpus store."""

from __future__ import annotations

import time
from collections import Counter

from ..models import Document, Section, Statistics


class IndexStore:
    """Holds the parsed corpus. Cheap to hold fully in memory at typical MkDocs scale."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.sections: list[Section] = []
        self.built_at: float = 0.0

    # ---- population ----------------------------------------------------
    def reset(self) -> None:
        self.documents.clear()
        self.sections.clear()

    def add_document(self, doc: Document, sections: list[Section]) -> None:
        start = len(self.sections)
        self.sections.extend(sections)
        doc.section_ids = list(range(start, len(self.sections)))
        self.documents[doc.page_id] = doc

    def finalize(self) -> None:
        self.built_at = time.time()

    # ---- lookups -------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return bool(self.documents)

    def get_doc(self, page_id: str) -> Document | None:
        return self.documents.get(page_id)

    def sections_of(self, page_id: str) -> list[Section]:
        doc = self.documents.get(page_id)
        if not doc:
            return []
        return [self.sections[i] for i in doc.section_ids]

    def index_age_seconds(self) -> float | None:
        return None if not self.built_at else time.time() - self.built_at

    # ---- stats ---------------------------------------------------------
    def statistics(self) -> Statistics:
        by_tenant: Counter[str] = Counter()
        by_doc_type: Counter[str] = Counter()
        by_topic: Counter[str] = Counter()
        for d in self.documents.values():
            by_tenant[d.tenant or "_global"] += 1
            by_doc_type[d.doc_type] += 1
            for t in d.topics:
                by_topic[t] += 1
        return Statistics(
            pages=len(self.documents),
            sections=len(self.sections),
            by_tenant=dict(by_tenant),
            by_doc_type=dict(by_doc_type),
            by_topic=dict(by_topic),
            index_built_at=(
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.built_at))
                if self.built_at
                else None
            ),
        )
