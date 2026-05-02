from __future__ import annotations

import json
from pathlib import Path

from llm_wiki.resolve import resolve_links
from llm_wiki.utils import markdown_with_frontmatter


def test_resolve_rewrites_simple_plural_link_to_canonical_title(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    build = tmp_path / ".wiki_build"
    vault.mkdir()
    (build / "index").mkdir(parents=True)
    (build / "index" / "pages.json").write_text(
        json.dumps([{"title": "Networks Business", "aliases": [], "tags": [], "source_path": "x.md"}]),
        encoding="utf-8",
    )
    page = vault / "sample.md"
    page.write_text(markdown_with_frontmatter({"title": "Sample"}, "See [[Networks Businesses]]."), encoding="utf-8")

    unresolved = resolve_links(vault, build)

    assert unresolved == []
    assert "[[Networks Business|Networks Businesses]]" in page.read_text(encoding="utf-8")

