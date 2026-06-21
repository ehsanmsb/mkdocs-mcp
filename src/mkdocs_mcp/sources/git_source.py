"""Primary source: clone/pull a docs repo, then read it via LocalSource.

Authentication
--------------
Supports three cases with one mechanism:

* **Public repo (GitHub or GitLab)** — leave ``git_token`` empty; the repo is
  cloned anonymously.
* **Private / Internal GitLab** — set ``git_token`` to a Personal Access Token
  (or Project/Group token). Default username ``oauth2`` is the GitLab convention.
* **Private GitHub** — set ``git_token`` to a PAT and ``git_username`` to your
  username or ``x-access-token``.

The token is sent as an HTTP Basic ``Authorization`` header injected through
git's ``GIT_CONFIG_*`` environment variables at command time. It is therefore
**never written to ``.git/config``** and **never appears in the process
argument list** — unlike embedding it in the clone URL. ``GIT_TERMINAL_PROMPT=0``
makes auth failures fail fast instead of hanging on a prompt.

Uses the ``git`` CLI (already in the image) to avoid a heavy git dependency.
"""

from __future__ import annotations

import asyncio
import base64
import os

from ..config import Settings
from ..obs.logging import get_logger
from .base import RawCorpus
from .local_source import LocalSource

log = get_logger(__name__)


async def _run(*args: str, cwd: str | None = None, env: dict | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        # Never echo the env (it may hold the auth header) — only the command.
        raise RuntimeError(f"{' '.join(args)} failed: {err.decode().strip()}")
    return out.decode()


class GitSource:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg
        self.local = LocalSource(cfg)

    def _auth_env(self) -> dict:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"  # fail instead of prompting
        if self.cfg.git_token:
            cred = f"{self.cfg.git_username}:{self.cfg.git_token}"
            header = "Authorization: Basic " + base64.b64encode(cred.encode()).decode()
            # Injected via env so it is not persisted to config nor visible in `ps`.
            env["GIT_CONFIG_COUNT"] = "1"
            env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
            env["GIT_CONFIG_VALUE_0"] = header
        return env

    async def _sync(self) -> None:
        env = self._auth_env()
        repo = self.cfg.repo_dir
        url = self.cfg.git_url  # plain URL — credentials travel in the auth header
        if os.path.isdir(os.path.join(repo, ".git")):
            await _run("git", "-C", repo, "remote", "set-url", "origin", url, env=env)
            await _run(
                "git", "-C", repo, "fetch", "--depth", "1", "origin", self.cfg.git_branch, env=env
            )
            await _run(
                "git", "-C", repo, "reset", "--hard", f"origin/{self.cfg.git_branch}", env=env
            )
        else:
            os.makedirs(os.path.dirname(repo) or ".", exist_ok=True)
            await _run(
                "git", "clone", "--depth", "1", "--branch", self.cfg.git_branch, url, repo, env=env
            )

    async def _commit(self) -> str | None:
        try:
            return (await _run("git", "-C", self.cfg.repo_dir, "rev-parse", "HEAD")).strip()
        except RuntimeError:
            return None

    async def _git_meta(self, rel_path: str) -> tuple[str | None, str | None]:
        docs_path = f"{self.cfg.docs_subdir}/{rel_path}"
        try:
            out = await _run(
                "git",
                "-C",
                self.cfg.repo_dir,
                "log",
                "-1",
                "--format=%aI%x09%an",
                "--",
                docs_path,
            )
            if out.strip():
                ts, _, author = out.strip().partition("\t")
                return ts or None, author or None
        except RuntimeError:
            pass
        return None, None

    async def load(self) -> RawCorpus:
        await self._sync()
        corpus = await self.local.load()
        corpus.commit = await self._commit()
        for page in corpus.pages:
            page.last_modified, page.author = await self._git_meta(page.rel_path)
        log.info("git_source_loaded", pages=len(corpus.pages), commit=corpus.commit)
        return corpus
