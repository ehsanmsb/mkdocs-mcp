"""Read docs from an already-present checkout (dev + tests + git pod volume)."""

from __future__ import annotations

import os

from ..config import Settings
from .base import RawCorpus, RawPage


class LocalSource:
    def __init__(self, cfg: Settings, repo_dir: str | None = None) -> None:
        self.cfg = cfg
        self.repo_dir = repo_dir or cfg.repo_dir

    async def load(self) -> RawCorpus:
        docs_dir = os.path.join(self.repo_dir, self.cfg.docs_subdir)
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

        nav_text: str | None = None
        cfg_path = os.path.join(self.repo_dir, self.cfg.mkdocs_config)
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                nav_text = f.read()

        return RawCorpus(pages=pages, nav_config_text=nav_text, commit=None)
