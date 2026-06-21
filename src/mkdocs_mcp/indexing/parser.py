"""Parse a markdown page into a title + heading-delimited sections.

- Frontmatter is parsed with ``python-frontmatter`` (the de-facto library).
- The markdown body is tokenized with ``markdown-it-py`` so we can reliably
  separate headings, body text, and fenced code blocks.

Splitting a page into heading-scoped sections is application logic (no library
produces exactly this chunking), so it is implemented here on top of the
library token stream.
"""

from __future__ import annotations

import frontmatter
from markdown_it import MarkdownIt

from ..models import CodeBlock, Section
from .metadata import Classifier
from .text import page_id_from_relpath, page_url, section_url, slugify

_md = MarkdownIt("commonmark")


class _Block:
    __slots__ = ("heading", "level", "lines", "code_blocks")

    def __init__(self, heading: str, level: int) -> None:
        self.heading = heading
        self.level = level
        self.lines: list[str] = []
        self.code_blocks: list[CodeBlock] = []


def parse_page(
    rel_path: str,
    raw: str,
    base_url: str,
    classifier: Classifier,
) -> tuple[str, list[Section], list[str], str]:
    """Return ``(page_title, sections, headings, content)``."""
    post = frontmatter.loads(raw)
    content = post.content
    meta_title = post.metadata.get("title")

    tokens = _md.parse(content)
    lines = content.splitlines()

    blocks: list[_Block] = [_Block(heading="", level=0)]  # intro block
    page_title = str(meta_title) if meta_title else ""

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.type == "heading_open":
            level = int(tok.tag[1])
            heading_text = tokens[i + 1].content.strip()
            if level == 1 and not page_title:
                page_title = heading_text
                i += 3
                continue
            blocks.append(_Block(heading=heading_text, level=level))
            i += 3
            continue
        if tok.type == "fence":
            blocks[-1].code_blocks.append(
                CodeBlock(language=(tok.info.strip() or None), code=tok.content)
            )
            blocks[-1].lines.append(tok.content)
            i += 1
            continue
        if tok.type == "inline" and tok.content:
            blocks[-1].lines.append(tok.content)
        elif tok.map:
            start, end = tok.map
            blocks[-1].lines.append("\n".join(lines[start:end]))
        i += 1

    if not page_title:
        page_title = page_id_from_relpath(rel_path).rsplit("/", 1)[-1].replace("-", " ").title()

    pid = page_id_from_relpath(rel_path)
    purl = page_url(base_url, rel_path)
    tenant = classifier.tenant_of(rel_path)
    dtype = classifier.doc_type_of(rel_path)
    topics = classifier.topics_of(rel_path, content)
    runbook = classifier.is_runbook(rel_path)

    sections: list[Section] = []
    headings: list[str] = []
    for b in blocks:
        text = "\n".join(line for line in b.lines if line).strip()
        if b.heading:
            headings.append(b.heading)
        if not text and not b.heading:
            continue
        anchor = slugify(b.heading) if b.heading else ""
        sections.append(
            Section(
                page_id=pid,
                page_title=page_title,
                heading=b.heading or page_title,
                level=b.level,
                anchor=anchor,
                url=section_url(purl, anchor),
                text=text,
                tenant=tenant,
                doc_type=dtype,
                topics=topics,
                is_runbook=runbook,
                code_blocks=b.code_blocks,
            )
        )

    return page_title, sections, headings, content
