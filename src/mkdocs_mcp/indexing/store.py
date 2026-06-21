"""In-memory corpus store + JSON snapshot persistence for warm restarts."""
from __future__ import annotations

import json
import os
import tempfile
import time
from collections import Counter

from ..models import Document, Section, Statistics, TreeNode
from .nav import Nav


class IndexStore:
    """Holds the parsed corpus. Cheap to hold fully in memory at typical MkDocs scale."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.sections: list[Section] = []
        self.nav: Nav = Nav.empty()
        self.commit: str | None = None
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

    def finalize(self, commit: str | None) -> None:
        self.commit = commit
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
            index_commit=self.commit,
            index_built_at=(
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.built_at))
                if self.built_at
                else None
            ),
        )

    # ---- navigation tree ----------------------------------------------
    def tree(self, tenant: str | None = None) -> list[TreeNode]:
        def conv(nodes: list[dict]) -> list[TreeNode]:
            out: list[TreeNode] = []
            for n in nodes:
                pid = n.get("page_id")
                doc = self.documents.get(pid) if pid else None
                node = TreeNode(
                    title=n.get("title", ""),
                    page_id=pid,
                    url=doc.url if doc else None,
                    children=conv(n.get("children", [])),
                )
                out.append(node)
            return out

        roots = conv(self.nav.tree)
        if tenant:
            roots = [r for r in roots if r.title.lower() == tenant.lower()]
        return roots

    # ---- snapshot ------------------------------------------------------
    def save_snapshot(self, path: str) -> None:
        payload = {
            "commit": self.commit,
            "built_at": self.built_at,
            "nav_tree": self.nav.tree,
            "nav_breadcrumbs": self.nav.breadcrumbs,
            "documents": [d.model_dump() for d in self.documents.values()],
            "sections": [s.model_dump() for s in self.sections],
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, path)  # atomic

    @classmethod
    def load_snapshot(cls, path: str) -> IndexStore | None:
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        store = cls()
        store.commit = payload.get("commit")
        store.built_at = payload.get("built_at", 0.0)
        store.nav.tree = payload.get("nav_tree", [])
        store.nav.breadcrumbs = payload.get("nav_breadcrumbs", {})
        store.sections = [Section(**s) for s in payload.get("sections", [])]
        for d in payload.get("documents", []):
            store.documents[d["page_id"]] = Document(**d)
        return store
