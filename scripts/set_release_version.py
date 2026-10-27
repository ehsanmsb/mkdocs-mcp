"""Keep source package, lockfile, and Helm chart at the released version."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def replace(path: Path, pattern: str, replacement: str) -> None:
    source = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Expected one version field in {path}")
    path.write_text(updated, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        raise SystemExit("Usage: python scripts/set_release_version.py MAJOR.MINOR.PATCH")

    version = sys.argv[1]
    replace(Path("pyproject.toml"), r'^version = "[^"]+"$', f'version = "{version}"')
    replace(
        Path("uv.lock"),
        r'(?<=name = "mkdocs-mcp"\n)version = "[^"]+"',
        f'version = "{version}"',
    )
    replace(Path("charts/mkdocs-mcp/Chart.yaml"), r"^version: \S+$", f"version: {version}")
    replace(
        Path("charts/mkdocs-mcp/Chart.yaml"),
        r'^appVersion: "[^"]+"$',
        f'appVersion: "{version}"',
    )


if __name__ == "__main__":
    main()
