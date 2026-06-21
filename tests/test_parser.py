from mkdocs_mcp.config import Settings
from mkdocs_mcp.indexing.metadata import Classifier
from mkdocs_mcp.indexing.parser import parse_page
from mkdocs_mcp.indexing.text import page_url, slugify

CLF = Classifier(Settings())


def test_slugify_matches_markdown_toc():
    assert slugify("Creating the Ingress") == "creating-the-ingress"
    assert slugify("Step 4: Initialize") == "step-4-initialize"


def test_page_url_directory_style():
    assert page_url("https://x", "index.md") == "https://x/"
    assert page_url("https://x", "a/b.md") == "https://x/a/b/"
    assert page_url("https://x", "a/index.md") == "https://x/a/"


def test_parse_splits_sections_and_code():
    raw = "# Title\n\nIntro text.\n\n## First\n\nbody\n\n```bash\nls -la\n```\n"
    title, sections, headings, _content = parse_page("a/b.md", raw, "https://x", CLF)
    assert title == "Title"
    assert headings == ["First"]
    first = next(s for s in sections if s.heading == "First")
    assert first.anchor == "first"
    assert first.url == "https://x/a/b/#first"
    assert first.code_blocks and first.code_blocks[0].language == "bash"


def test_frontmatter_parsed_and_title_used():
    raw = "---\ntitle: Real Title\n---\n## Body\n\ncontent\n"
    title, _sections, _headings, content = parse_page("a.md", raw, "https://x", CLF)
    assert title == "Real Title"
    assert "title: Real Title" not in content
