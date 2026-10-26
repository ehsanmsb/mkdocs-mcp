"""Read a local MkDocs project for development and tests."""

from __future__ import annotations

import os

from ..config import Settings
from .base import RawCorpus, RawPage


class LocalSource:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg

    async def load(self) -> RawCorpus:
        docs_dir = os.path.join(self.cfg.local_dir, self.cfg.docs_subdir)
        pages: list[RawPage] = []
        for root, _dirs, files in os.walk(docs_dir):
            for name in files:
                if not name.endswith(".md"):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, docs_dir).replace(os.sep, "/")
                with open(full, encoding="utf-8") as f:
                    raw = f.read()
                pages.append(RawPage(rel_path=rel, raw=raw))
        pages.sort(key=lambda p: p.rel_path)

        return RawCorpus(pages=pages)
