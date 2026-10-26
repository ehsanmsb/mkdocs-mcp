"""Orchestrates: source.load() -> parse -> build store -> attach to engine.

Also owns conditional refresh of the published search corpus.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urljoin

from markdown_it import MarkdownIt

from ..config import Settings
from ..models import CodeBlock, Document, Section
from ..obs import metrics
from ..obs.logging import get_logger
from ..search.engine import SearchEngine
from ..sources.base import RawPage, Source
from ..sources.local_source import LocalSource
from ..sources.search_index_source import SearchIndexSource
from .metadata import Classifier
from .parser import parse_page
from .store import IndexStore
from .text import page_id_from_relpath, page_url

log = get_logger(__name__)
_md = MarkdownIt("commonmark")


def make_source(cfg: Settings) -> Source:
    if cfg.source_mode == "search_index":
        return SearchIndexSource(cfg)
    return LocalSource(cfg)


def _published_page(
    page: RawPage, cfg: Settings, classifier: Classifier
) -> tuple[str, list[Section], list[str], str, str]:
    """Map each published search entry to exactly one searchable section."""
    entries = page.published_entries or []
    title = entries[0][0]
    pid = page_id_from_relpath(page.rel_path)
    base = f"{cfg.base_url.rstrip('/')}/"
    page_url_ = urljoin(base, entries[0][2].split("#", 1)[0])
    tenant = classifier.tenant_of(page.rel_path)
    doc_type = classifier.doc_type_of(page.rel_path)
    topics = classifier.topics_of(page.rel_path, page.raw)
    is_runbook = classifier.is_runbook(page.rel_path)
    headings: list[str] = []
    sections: list[Section] = []
    for label, body, location in entries:
        anchor = location.split("#", 1)[1] if "#" in location else ""
        if anchor:
            headings.append(label)
        code_blocks = [
            CodeBlock(language=token.info.strip() or None, code=token.content)
            for token in _md.parse(body)
            if token.type == "fence"
        ]
        sections.append(
            Section(
                page_id=pid,
                page_title=title,
                heading=label or title,
                level=2 if anchor else 0,
                anchor=anchor,
                url=urljoin(base, location),
                text=body,
                tenant=tenant,
                doc_type=doc_type,
                topics=topics,
                is_runbook=is_runbook,
                code_blocks=code_blocks,
            )
        )
    return title, sections, headings, page.raw, page_url_


class Indexer:
    def __init__(self, cfg: Settings, engine: SearchEngine, classifier: Classifier) -> None:
        self.cfg = cfg
        self.engine = engine
        self.classifier = classifier
        self.source = make_source(cfg)
        self._task: asyncio.Task | None = None

    async def build(self) -> IndexStore:
        t0 = time.time()
        corpus = await self.source.load()
        if corpus is None:
            log.info("search_index_unchanged")
            return self.engine.store
        store = IndexStore()
        for page in corpus.pages:
            pid = page_id_from_relpath(page.rel_path)
            if page.published_entries is not None:
                title, sections, headings, content, published_url = _published_page(
                    page, self.cfg, self.classifier
                )
            else:
                title, sections, headings, content = parse_page(
                    page.rel_path, page.raw, self.cfg.base_url, self.classifier
                )
                published_url = page_url(self.cfg.base_url, page.rel_path)
            first = sections[0] if sections else None
            doc = Document(
                page_id=pid,
                title=title,
                rel_path=page.rel_path,
                url=published_url,
                tenant=first.tenant if first else None,
                doc_type=first.doc_type if first else "guide",
                topics=first.topics if first else [],
                is_runbook=first.is_runbook if first else False,
                headings=headings,
                content=content,
            )
            store.add_document(doc, sections)

        store.finalize()
        self.engine.attach(store, vocab=self.classifier.vocab)
        if isinstance(self.source, SearchIndexSource):
            self.source.accept()

        dur = int((time.time() - t0) * 1000)
        metrics.REINDEX.labels(status="ok").inc()
        metrics.INDEX_AGE.set(0)
        log.info(
            "index_built",
            pages=len(store.documents),
            sections=len(store.sections),
            duration_ms=dur,
        )
        return store

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
