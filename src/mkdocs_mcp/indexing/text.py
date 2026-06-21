"""Small text helpers: heading anchors, MkDocs URL building, snippets.

Anchor generation reuses python-markdown's own ``toc`` slugify so that the
``#fragment`` we emit matches the anchors MkDocs actually renders (python-mark
down is what MkDocs uses under the hood).
"""
from __future__ import annotations

import re

from markdown.extensions.toc import slugify as _md_slugify
from markdown.extensions.toc import slugify_unicode as _md_slugify_unicode

_WS = re.compile(r"\s+")


def slugify(text: str, unicode: bool = False) -> str:
    """Heading -> URL anchor, identical to python-markdown's toc extension."""
    fn = _md_slugify_unicode if unicode else _md_slugify
    return fn(text, "-")


def page_id_from_relpath(rel_path: str) -> str:
    """``a/b/user-guide.md`` -> ``a/b/user-guide``; ``index.md`` -> ``index``."""
    return rel_path[:-3] if rel_path.endswith(".md") else rel_path


def page_url(base_url: str, rel_path: str) -> str:
    """Build a MkDocs directory-style URL for a page.

    ``index.md``   -> ``{base}/``
    ``a/b.md``     -> ``{base}/a/b/``
    ``a/index.md`` -> ``{base}/a/``
    """
    base = base_url.rstrip("/")
    pid = page_id_from_relpath(rel_path)
    if pid == "index":
        return f"{base}/"
    if pid.endswith("/index"):
        return f"{base}/{pid[: -len('/index')]}/"
    return f"{base}/{pid}/"


def section_url(page_url_: str, anchor: str) -> str:
    return f"{page_url_}#{anchor}" if anchor else page_url_


def make_snippet(text: str, query_terms: list[str], width: int = 240) -> str:
    """Window the text around the first matching query term."""
    if not text:
        return ""
    lowered = text.lower()
    pos = -1
    for t in query_terms:
        p = lowered.find(t.lower())
        if p != -1 and (pos == -1 or p < pos):
            pos = p
    start = max(0, pos - 80) if pos != -1 else 0
    snippet = _WS.sub(" ", text[start : start + width].strip())
    prefix = "…" if start > 0 else ""
    suffix = "…" if start + width < len(text) else ""
    return f"{prefix}{snippet}{suffix}"
