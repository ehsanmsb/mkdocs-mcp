"""Orchestrates: source.load() -> parse -> build store -> attach to engine.

Also owns snapshot warm-load and the periodic re-index scheduler.
"""
from __future__ import annotations

import asyncio
import time

from ..config import Settings
from ..models import Document
from ..obs import metrics
from ..obs.logging import get_logger
from ..search.engine import SearchEngine
from ..sources.base import Source
from ..sources.git_source import GitSource
from ..sources.local_source import LocalSource
from ..sources.search_index_source import SearchIndexSource
from .metadata import Classifier
from .nav import Nav
from .parser import parse_page
from .store import IndexStore
from .text import page_id_from_relpath, page_url

log = get_logger(__name__)


def make_source(cfg: Settings) -> Source:
    if cfg.source_mode == "git":
        return GitSource(cfg)
    if cfg.source_mode == "search_index":
        return SearchIndexSource(cfg)
    return LocalSource(cfg)


class Indexer:
    def __init__(self, cfg: Settings, engine: SearchEngine, classifier: Classifier) -> None:
        self.cfg = cfg
        self.engine = engine
        self.classifier = classifier
        self.source = make_source(cfg)
        self._task: asyncio.Task | None = None

    def _edit_url(self, rel_path: str) -> str | None:
        if not self.cfg.repo_web_url:
            return None
        suffix = self.cfg.edit_uri_template.format(
            branch=self.cfg.edit_branch,
            docs_subdir=self.cfg.docs_subdir,
            rel_path=rel_path,
        )
        return f"{self.cfg.repo_web_url.rstrip('/')}{suffix}"

    async def build(self) -> IndexStore:
        t0 = time.time()
        corpus = await self.source.load()
        store = IndexStore()
        store.nav = (
            Nav.from_config_text(corpus.nav_config_text)
            if corpus.nav_config_text
            else Nav.empty()
        )

        for page in corpus.pages:
            title, sections, headings, content = parse_page(
                page.rel_path, page.raw, self.cfg.base_url, self.classifier
            )
            pid = page_id_from_relpath(page.rel_path)
            first = sections[0] if sections else None
            breadcrumb = store.nav.breadcrumbs.get(pid, [])
            doc = Document(
                page_id=pid,
                title=title,
                rel_path=page.rel_path,
                url=page_url(self.cfg.base_url, page.rel_path),
                edit_url=self._edit_url(page.rel_path),
                breadcrumb=breadcrumb,
                tenant=first.tenant if first else None,
                doc_type=first.doc_type if first else "guide",
                topics=first.topics if first else [],
                is_runbook=first.is_runbook if first else False,
                headings=headings,
                content=content,
                last_modified=page.last_modified,
                author=page.author,
            )
            store.add_document(doc, sections)

        store.finalize(corpus.commit)
        self.engine.attach(store, vocab=self.classifier.vocab)
        try:
            store.save_snapshot(self.cfg.snapshot_path)
        except OSError as exc:  # snapshot is best-effort
            log.warning("snapshot_save_failed", error=str(exc))

        dur = int((time.time() - t0) * 1000)
        metrics.REINDEX.labels(status="ok").inc()
        metrics.INDEX_AGE.set(0)
        log.info(
            "index_built",
            pages=len(store.documents),
            sections=len(store.sections),
            commit=store.commit,
            duration_ms=dur,
        )
        return store

    async def warm_load(self) -> bool:
        """Load a persisted snapshot so we serve immediately after restart."""
        store = IndexStore.load_snapshot(self.cfg.snapshot_path)
        if store and store.is_loaded:
            self.engine.attach(store, vocab=self.classifier.vocab)
            log.info("warm_loaded", pages=len(store.documents), commit=store.commit)
            return True
        return False

    async def safe_build(self) -> None:
        try:
            await self.build()
        except Exception as exc:  # noqa: BLE001 - keep serving stale index
            metrics.REINDEX.labels(status="error").inc()
            log.error("index_build_failed", error=str(exc))

    async def _loop(self) -> None:
        interval = self.cfg.reindex_interval_minutes * 60
        while interval > 0:
            await asyncio.sleep(interval)
            log.info("scheduled_reindex_start")
            await self.safe_build()

    def start_scheduler(self) -> None:
        if self.cfg.reindex_interval_minutes > 0 and self._task is None:
            self._task = asyncio.create_task(self._loop())
