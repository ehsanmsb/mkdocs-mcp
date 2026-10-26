"""Published and local documentation source records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawPage:
    rel_path: str  # path relative to the docs dir, e.g. "guides/deployment.md"
    raw: str  # Markdown, or a readable reconstruction of published search text
    published_entries: list[tuple[str, str, str]] | None = None  # title, text, location


@dataclass
class RawCorpus:
    pages: list[RawPage] = field(default_factory=list)


class Source(Protocol):
    async def load(self) -> RawCorpus | None: ...
