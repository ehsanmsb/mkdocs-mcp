"""Orchestrates: fetch published index -> build store -> attach to engine.

Also owns conditional refresh of the published search corpus.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from urllib.parse import urljoin

from markdown_it import MarkdownIt

from ..config import Settings
from ..models import CodeBlock, Document, Section
from ..obs import metrics
from ..obs.logging import get_logger
from ..search.engine import SearchEngine
from ..sources.base import RawCorpus, RawPage
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


def _published_page(
    page: RawPage, base_url: str, page_id: str, site: str
) -> tuple[str, list[Section], list[str], str, str]:
    """Map each published search entry to exactly one searchable section."""
    entries = page.published_entries
    title = entries[0][0]
    base = f"{base_url.rstrip('/')}/"
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
                page_id=page_id,
                site=site,
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
        self.sites = cfg.sites
        self.sources = {
            site.name: SearchIndexSource(site.base_url, site.search_index_url)
            for site in self.sites
        }
        self.corpora: dict[str, RawCorpus] = {}
        self.failed_sites: list[str] = []
        self._task: asyncio.Task | None = None

    async def build(self) -> IndexStore:
        start = time.perf_counter()
        try:
            return await self._build(start)
        except Exception as exc:
            metrics.INDEX_REFRESH.labels(result="error").inc()
            log.error(
                "index_refresh_failed",
                error_type=type(exc).__name__,
                error=str(exc)[:240],
                retained_pages=len(self.engine.store.documents),
            )
            raise
        finally:
            metrics.INDEX_REFRESH_DURATION.observe(time.perf_counter() - start)

    async def _build(self, start: float) -> IndexStore:
        results = await asyncio.gather(
            *(self.sources[site.name].load() for site in self.sites), return_exceptions=True
        )
        corpora = self.corpora.copy()
        updated: list[str] = []
        failed: list[str] = []
        for site, result in zip(self.sites, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                failed.append(site.name)
                log.error(
                    "site_refresh_failed",
                    site=site.name,
                    error_type=type(result).__name__,
                    error=str(result)[:240],
                )
            elif result is not None:
                corpora[site.name] = result
                updated.append(site.name)
            elif site.name not in corpora:
                failed.append(site.name)
                log.error("site_refresh_failed", site=site.name, error="304 without a cached index")
        self.failed_sites = failed
        if not corpora:
            raise RuntimeError("No documentation sites could be loaded")
        if failed:
            metrics.INDEX_REFRESH.labels(result="error").inc()
        if not updated and self.engine.store.is_loaded:
            if not failed:
                metrics.INDEX_REFRESH.labels(result="unchanged").inc()
            metrics.INDEX_LAST_CHECK.set(time.time())
            log.debug("index_unchanged", failed_sites=failed)
            return self.engine.store
        store = IndexStore()
        for site in self.sites:
            corpus = corpora.get(site.name)
            if corpus is None:
                continue
            for page in corpus.pages:
                rel_id = page_id_from_relpath(page.rel_path)
                page_id = f"{site.name}:{rel_id}"
                title, sections, headings, content, published_url = _published_page(
                    page, site.base_url, page_id, site.name
                )
                first = sections[0] if sections else None
                doc = Document(
                    page_id=page_id,
                    site=site.name,
                    title=title,
                    url=published_url,
                    doc_type=first.doc_type if first else "guide",
                    headings=headings,
                    content=content,
                )
                store.add_document(doc, sections)

        store.finalize()
        self.engine.attach(store)
        self.corpora = corpora
        for name in updated:
            self.sources[name].accept()

        dur = round((time.perf_counter() - start) * 1000)
        metrics.INDEX_REFRESH.labels(result="updated").inc()
        metrics.INDEX_LAST_CHECK.set(time.time())
        metrics.INDEX_LAST_BUILD.set(store.built_at)
        metrics.INDEX_READY.set(1)
        log.info(
            "index_updated",
            pages=len(store.documents),
            sections=len(store.sections),
            sites_loaded=len(corpora),
            sites_failed=failed,
            duration_ms=dur,
        )
        return store

    async def safe_build(self) -> None:
        with contextlib.suppress(Exception):  # Keep serving the last good index.
            await self.build()

    async def _loop(self) -> None:
        interval = self.cfg.reindex_interval_minutes * 60
        while interval > 0:
            await asyncio.sleep(interval)
            await self.safe_build()

    def start_scheduler(self) -> None:
        if self.cfg.reindex_interval_minutes > 0 and self._task is None:
            self._task = asyncio.create_task(self._loop())
