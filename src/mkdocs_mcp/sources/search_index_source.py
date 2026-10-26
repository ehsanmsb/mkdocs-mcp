"""Read the published MkDocs search corpus without cloning its source repo."""

from __future__ import annotations

from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from ..config import Settings
from ..obs.logging import get_logger
from .base import RawCorpus, RawPage

log = get_logger(__name__)


class _ReadableHTML(HTMLParser):
    """Keep readable text and fenced code from MkDocs' rendered search text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.in_pre = False
        self.in_code = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self.in_pre = True
            self.parts.append("\n\n")
        elif tag == "code" and self.in_pre:
            classes = dict(attrs).get("class") or ""
            language = next((c[9:] for c in classes.split() if c.startswith("language-")), "")
            self.parts.append(f"```{language}\n")
            self.in_code = True
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in {"p", "div", "ol", "ul", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "code" and self.in_code:
            self.parts.append("\n```\n")
            self.in_code = False
        elif tag == "pre":
            self.in_pre = False
            self.parts.append("\n")
        elif tag in {"p", "div", "li", "ol", "ul", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def readable_text(value: str) -> str:
    parser = _ReadableHTML()
    parser.feed(value)
    parser.close()
    out: list[str] = []
    in_code = False
    for line in "".join(parser.parts).splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line.strip())
        elif in_code:
            out.append(line.rstrip())
        elif line.strip():
            out.append(line.strip())
    return "\n".join(out)


def _page_path(location: str) -> str:
    path = location.split("#", 1)[0].strip("/")
    if urlsplit(location).scheme or location.startswith("//") or ".." in path.split("/"):
        raise ValueError(f"Invalid search index location: {location!r}")
    return path


def _location_to_relpath(location: str) -> str:
    path = _page_path(location)
    return f"{path}.md" if path else "index.md"


class SearchIndexSource:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.etag: str | None = None
        self.last_modified: str | None = None
        self._pending: tuple[str | None, str | None] | None = None

    async def load(self) -> RawCorpus | None:
        url = self.cfg.search_index_url or (
            f"{self.cfg.base_url.rstrip('/')}/search/search_index.json"
        )
        headers = {}
        if self.etag:
            headers["If-None-Match"] = self.etag
        elif self.last_modified:
            headers["If-Modified-Since"] = self.last_modified
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 304:
                return None
            resp.raise_for_status()
            data = resp.json()

        if not isinstance(data, dict) or not isinstance(data.get("docs"), list) or not data["docs"]:
            raise ValueError("MkDocs search index has no docs")

        pages: dict[str, dict] = defaultdict(
            lambda: {"title": "", "intro": "", "location": "", "sections": []}
        )
        for entry in data["docs"]:
            if not isinstance(entry, dict):
                raise ValueError("Invalid MkDocs search index entry")
            location = entry.get("location")
            title = entry.get("title")
            body = entry.get("text")
            if not all(isinstance(v, str) for v in (location, title, body)):
                raise ValueError("MkDocs search entries need string location, title and text")
            rel = _location_to_relpath(location)
            bucket = pages[rel]
            if "#" in location:
                bucket["sections"].append((title, readable_text(body), location))
            else:
                bucket["title"] = title
                bucket["intro"] = readable_text(body)
                bucket["location"] = location

        raw_pages: list[RawPage] = []
        for rel, bucket in pages.items():
            if not bucket["location"] and rel != "index.md":
                bucket["location"] = bucket["sections"][0][2].split("#", 1)[0]
            if not bucket["title"]:
                slug = rel.rsplit("/", 1)[-1].removesuffix(".md")
                bucket["title"] = slug.replace("-", " ").title()
            lines = [f"# {bucket['title']}".rstrip(), "", bucket["intro"], ""]
            for title, body, _location in bucket["sections"]:
                lines.extend((f"## {title}".rstrip(), "", body, ""))
            entries = [(bucket["title"], bucket["intro"], bucket["location"])]
            entries.extend(bucket["sections"])
            raw_pages.append(
                RawPage(
                    rel_path=rel,
                    raw="\n".join(lines),
                    published_entries=entries,
                )
            )

        raw_pages.sort(key=lambda page: page.rel_path)
        self._pending = (resp.headers.get("ETag"), resp.headers.get("Last-Modified"))
        log.info("search_index_loaded", pages=len(raw_pages), entries=len(data["docs"]))
        return RawCorpus(pages=raw_pages)

    def accept(self) -> None:
        if self._pending is not None:
            self.etag, self.last_modified = self._pending
            self._pending = None
