"""Orchestrates: fetch published index -> build store -> attach to engine.

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
from ..sources.base import RawPage
from ..sources.search_index_source import SearchIndexSource
from .store import IndexStore
from .text import page_id_from_relpath

log = get_logger(__name__)
_md = MarkdownIt("commonmark")


def _doc_type(rel_path: str) -> str:
    path = "/" + rel_path.lower()
    if "/runbooks/" in path or "/runbook/" in path:
        return "runbook"
    if "/tutorials/" in path or "/tutorial/" in path:
        return "tutorial"
    if "troubleshoot" in path:
        return "troubleshooting"
    if any(part in path for part in ("/reference/", "/templates/", "/api/")):
        return "reference"
    return "guide"


def _published_page(page: RawPage, cfg: Settings) -> tuple[str, list[Section], list[str], str, str]:
    """Map each published search entry to exactly one searchable section."""
    entries = page.published_entries
    title = entries[0][0]
    pid = page_id_from_relpath(page.rel_path)
    base = f"{cfg.base_url.rstrip('/')}/"
    page_url_ = urljoin(base, entries[0][2].split("#", 1)[0])
    doc_type = _doc_type(page.rel_path)
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
                anchor=anchor,
                url=urljoin(base, location),
                text=body,
                doc_type=doc_type,
                code_blocks=code_blocks,
            )
        )
    return title, sections, headings, page.raw, page_url_


class Indexer:
    def __init__(self, cfg: Settings, engine: SearchEngine) -> None:
        self.cfg = cfg
        self.engine = engine
        self.source = SearchIndexSource(cfg)
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
            title, sections, headings, content, published_url = _published_page(page, self.cfg)
            first = sections[0] if sections else None
            doc = Document(
                page_id=pid,
                title=title,
                url=published_url,
                doc_type=first.doc_type if first else "guide",
                headings=headings,
                content=content,
            )
            store.add_document(doc, sections)

        store.finalize()
        self.engine.attach(store)
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
