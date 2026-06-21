"""Secondary / fallback source: the published MkDocs ``search_index.json``.

Zero dependency on git or a local checkout — works against the live site. The
index is flat (one entry per page + per section), so we reconstruct lightweight
markdown per page and let the normal parser re-split it. Git history and exact
code-block languages are not available from this source.
"""

from __future__ import annotations

from collections import defaultdict

import httpx

from ..config import Settings
from ..obs.logging import get_logger
from .base import RawCorpus, RawPage

log = get_logger(__name__)


def _location_to_relpath(location: str) -> str:
    """``guides/deployment/`` -> ``guides/deployment.md``; ``""`` -> ``index.md``."""
    loc = location.split("#", 1)[0].strip("/")
    if not loc:
        return "index.md"
    return f"{loc}.md"


class SearchIndexSource:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg

    async def load(self) -> RawCorpus:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.cfg.search_index_url)
            resp.raise_for_status()
            data = resp.json()

        # Group entries by their page location.
        pages: dict[str, dict] = defaultdict(lambda: {"title": "", "intro": "", "sections": []})
        for entry in data.get("docs", []):
            location = entry.get("location", "")
            rel = _location_to_relpath(location)
            title = entry.get("title", "")
            text = entry.get("text", "")
            bucket = pages[rel]
            if "#" not in location:
                bucket["title"] = title
                bucket["intro"] = text
            else:
                bucket["sections"].append((title, text))

        raw_pages: list[RawPage] = []
        for rel, bucket in pages.items():
            lines = [f"# {bucket['title']}".rstrip(), "", bucket["intro"], ""]
            for stitle, stext in bucket["sections"]:
                lines += [f"## {stitle}".rstrip(), "", stext, ""]
            raw_pages.append(RawPage(rel_path=rel, raw="\n".join(lines)))

        raw_pages.sort(key=lambda p: p.rel_path)
        log.info("search_index_loaded", pages=len(raw_pages))
        return RawCorpus(pages=raw_pages, nav_config_text=None, commit=None)
