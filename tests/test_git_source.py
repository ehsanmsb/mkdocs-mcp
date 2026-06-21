import base64

from mkdocs_mcp.config import Settings
from mkdocs_mcp.sources.git_source import GitSource


def test_public_repo_has_no_auth_header():
    gs = GitSource(Settings(source_mode="git", git_url="https://github.com/org/repo.git"))
    env = gs._auth_env()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "GIT_CONFIG_COUNT" not in env  # anonymous: no Authorization header


def test_gitlab_pat_builds_basic_header():
    gs = GitSource(Settings(git_token="glpat-xxx", git_username="oauth2"))
    env = gs._auth_env()
    assert env["GIT_CONFIG_KEY_0"] == "http.extraHeader"
    expected = "Authorization: Basic " + base64.b64encode(b"oauth2:glpat-xxx").decode()
    assert env["GIT_CONFIG_VALUE_0"] == expected


def test_github_pat_uses_configured_username():
    gs = GitSource(Settings(git_token="ghp_xxx", git_username="x-access-token"))
    env = gs._auth_env()
    expected = "Authorization: Basic " + base64.b64encode(b"x-access-token:ghp_xxx").decode()
    assert env["GIT_CONFIG_VALUE_0"] == expected
