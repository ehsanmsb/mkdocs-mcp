"""Published documentation source records."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawPage:
    rel_path: str  # path relative to the docs dir, e.g. "guides/deployment.md"
    raw: str  # readable reconstruction of published search text
    published_entries: list[tuple[str, str, str]]  # title, text, location


@dataclass
class RawCorpus:
    pages: list[RawPage] = field(default_factory=list)
