"""Source adapter interface.

A source yields the raw corpus that the indexer parses. Keeping this behind a
Protocol lets us swap git / search_index / local without touching the tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawPage:
    rel_path: str  # path relative to the docs dir, e.g. "guides/deployment.md"
    raw: str  # markdown source
    last_modified: str | None = None
    author: str | None = None


@dataclass
class RawCorpus:
    pages: list[RawPage] = field(default_factory=list)
    nav_config_text: str | None = None  # contents of mkdocs.<env>.yaml (if available)
    commit: str | None = None


class Source(Protocol):
    async def load(self) -> RawCorpus: ...
