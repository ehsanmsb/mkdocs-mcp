"""Shared singletons passed to every tool module.

Per-tool timing, logging, error handling, rate limiting and metrics are all
handled by FastMCP middleware (see ``server.py``), so tools stay free of
cross-cutting boilerplate.
"""
from __future__ import annotations

from .config import Settings
from .indexing.indexer import Indexer
from .indexing.metadata import Classifier
from .search.engine import SearchEngine


class AppContext:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.classifier = Classifier(cfg)
        self.engine = SearchEngine(cfg)
        self.indexer = Indexer(cfg, self.engine, self.classifier)

    @property
    def store(self):
        return self.engine.store

    def ensure_loaded(self) -> None:
        if not self.store.is_loaded:
            raise RuntimeError(
                "Documentation index is not ready yet. Try again shortly or call "
                "rebuild_index."
            )
