import pytest

from mkdocs_mcp.auth import build_verifier
from mkdocs_mcp.config import Settings


def test_public_mode_needs_no_token():
    assert build_verifier(Settings(auth_mode="none")) is None


def test_bearer_mode_without_tokens_fails_closed():
    with pytest.raises(ValueError, match="requires at least one"):
        build_verifier(Settings(auth_mode="bearer", bearer_tokens="", admin_tokens=""))
