"""Parse the MkDocs ``nav:`` tree into breadcrumbs + a navigation tree.

MkDocs config files contain ``!!python/name:...`` tags (in markdown_extensions),
so we register a permissive loader that ignores unknown YAML tags.
"""

from __future__ import annotations

from typing import Any

import yaml

from .text import page_id_from_relpath


class _PermissiveLoader(yaml.SafeLoader):
    pass


def _ignore_unknown(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node) -> None:
    return None


# Catch ``!!python/...`` and any other custom tag -> None.
_PermissiveLoader.add_multi_constructor("tag:yaml.org,2002:python/", _ignore_unknown)
_PermissiveLoader.add_multi_constructor("!", _ignore_unknown)


class Nav:
    """Holds breadcrumbs per page and the raw nav tree."""

    def __init__(self) -> None:
        # page_id -> list of category titles (excludes the page's own title)
        self.breadcrumbs: dict[str, list[str]] = {}
        # nested tree: list of {title, page_id?, children?}
        self.tree: list[dict[str, Any]] = []

    @classmethod
    def from_config_text(cls, text: str) -> Nav:
        data = yaml.load(text, Loader=_PermissiveLoader) or {}
        nav = cls()
        raw = data.get("nav") or []
        nav.tree = nav._walk(raw, trail=[])
        return nav

    @classmethod
    def empty(cls) -> Nav:
        return cls()

    def _walk(self, items: list[Any], trail: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, str):
                # bare path string in nav
                pid = page_id_from_relpath(item)
                self.breadcrumbs[pid] = list(trail)
                out.append({"title": pid.rsplit("/", 1)[-1], "page_id": pid})
            elif isinstance(item, dict):
                for title, value in item.items():
                    if isinstance(value, str):
                        pid = page_id_from_relpath(value)
                        self.breadcrumbs[pid] = list(trail)
                        out.append({"title": title, "page_id": pid})
                    elif isinstance(value, list):
                        children = self._walk(value, trail + [title])
                        out.append({"title": title, "children": children})
        return out
