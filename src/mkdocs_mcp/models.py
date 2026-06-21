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
    level: int  # heading depth (1..6); 0 for the intro block
    anchor: str  # slug used in the URL fragment
    url: str  # deep link with #anchor
    breadcrumb: list[str] = Field(default_factory=list)
    text: str
    tenant: str | None = None
    doc_type: DocType = "guide"
    topics: list[str] = Field(default_factory=list)
    is_runbook: bool = False
    code_blocks: list[CodeBlock] = Field(default_factory=list)


class Document(BaseModel):
    """A full page."""

    page_id: str
    title: str
    rel_path: str  # path relative to docs_dir, e.g. "guides/deployment.md"
    url: str
    edit_url: str | None = None
    breadcrumb: list[str] = Field(default_factory=list)
    tenant: str | None = None
    doc_type: DocType = "guide"
    topics: list[str] = Field(default_factory=list)
    is_runbook: bool = False
    headings: list[str] = Field(default_factory=list)
    content: str = ""
    last_modified: str | None = None  # ISO8601
    author: str | None = None
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
    tenant: str | None = None
    score: float


class PageRef(BaseModel):
    page_id: str
    title: str
    url: str
    doc_type: DocType
    tenant: str | None = None
    topics: list[str] = Field(default_factory=list)


class PageContent(BaseModel):
    page_id: str
    title: str
    breadcrumb: list[str]
    url: str
    edit_url: str | None = None
    tenant: str | None = None
    doc_type: DocType
    topics: list[str]
    headings: list[str]
    last_modified: str | None = None
    author: str | None = None
    content: str


class SectionContent(BaseModel):
    page_id: str
    heading: str
    url: str
    text: str
    prev_heading: str | None = None
    next_heading: str | None = None


class TreeNode(BaseModel):
    title: str
    page_id: str | None = None
    url: str | None = None
    children: list[TreeNode] = Field(default_factory=list)


class ChangeEntry(BaseModel):
    page_id: str
    title: str
    url: str
    last_modified: str | None = None
    author: str | None = None


class ReadingItem(BaseModel):
    order: int
    page_id: str
    title: str
    url: str
    doc_type: DocType
    why: str


class Statistics(BaseModel):
    pages: int
    sections: int
    by_tenant: dict[str, int]
    by_doc_type: dict[str, int]
    by_topic: dict[str, int]
    index_commit: str | None = None
    index_built_at: str | None = None


class HealthStatus(BaseModel):
    status: str  # ok | degraded | error
    index_loaded: bool
    index_age_seconds: float | None = None
    pages: int
    sections: int
    last_commit: str | None = None
    vector_enabled: bool


class RebuildResult(BaseModel):
    status: str
    pages: int
    sections: int
    duration_ms: int
    commit: str | None = None


TreeNode.model_rebuild()
