"""Release version changes stay in sync across Python and Helm metadata."""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


def test_source_versions_match():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    lock = tomllib.loads((root / "uv.lock").read_text())
    chart = (root / "charts/mkdocs-mcp/Chart.yaml").read_text()
    version = project["project"]["version"]
    assert next(p["version"] for p in lock["package"] if p["name"] == "mkdocs-mcp") == version
    assert f'version: {version}\nappVersion: "{version}"' in chart


def test_set_release_version(tmp_path):
    root = Path(__file__).resolve().parents[1]
    paths = ["pyproject.toml", "uv.lock", "charts/mkdocs-mcp/Chart.yaml"]
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(root / name, target)

    subprocess.run(
        [sys.executable, str(root / "scripts/set_release_version.py"), "5.2.3"],
        cwd=tmp_path,
        check=True,
    )

    assert 'version = "5.2.3"' in (tmp_path / "pyproject.toml").read_text()
    assert 'name = "mkdocs-mcp"\nversion = "5.2.3"' in (tmp_path / "uv.lock").read_text()
    chart = (tmp_path / "charts/mkdocs-mcp/Chart.yaml").read_text()
    assert 'version: 5.2.3\nappVersion: "5.2.3"' in chart
