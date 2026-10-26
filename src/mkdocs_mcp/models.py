"""Domain + tool I/O models.

Internal records (``Document``, ``Section``) are the indexed corpus.
The ``*Result`` / ``*Hit`` models are the tool-facing schemas returned to MCP
clients; keep them small and self-describing.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DocType = str  # guide | runbook | tutorial | troubleshooting | reference


class CodeBlock(BaseModel):
    language: str | None = None
    code: str


class Section(BaseModel):
    """A single heading-delimited chunk of a page — the unit of retrieval."""

    page_id: str  # e.g. "guides/deployment"
    page_title: str
    heading: str  # the section heading text ("" for the page intro)
    anchor: str  # slug used in the URL fragment
    url: str  # deep link with #anchor
    text: str
    doc_type: DocType = "guide"
    code_blocks: list[CodeBlock] = Field(default_factory=list)


class Document(BaseModel):
    """A full page."""

    page_id: str
    title: str
    url: str
    doc_type: DocType = "guide"
    headings: list[str] = Field(default_factory=list)
    content: str = ""
    section_ids: list[int] = Field(default_factory=list)  # indices into the store


# --------------------------------------------------------------------------- #
# Tool-facing schemas
# --------------------------------------------------------------------------- #
class SearchHit(BaseModel):
    page_id: str
    title: str
    heading: str
    breadcrumb: list[str]
    url: str
    snippet: str
    doc_type: DocType
    score: float


class PageRef(BaseModel):
    page_id: str
    title: str
    url: str
    doc_type: DocType


class PageContent(BaseModel):
    page_id: str
    title: str
    breadcrumb: list[str]
    url: str
    doc_type: DocType
    headings: list[str]
    content: str


class SectionContent(BaseModel):
    page_id: str
    heading: str
    url: str
    text: str
    prev_heading: str | None = None
    next_heading: str | None = None


class Statistics(BaseModel):
    pages: int
    sections: int
    by_doc_type: dict[str, int]
    index_built_at: str | None = None


class HealthStatus(BaseModel):
    status: str  # ok | degraded | error
    index_loaded: bool
    index_age_seconds: float | None = None
    pages: int
    sections: int
