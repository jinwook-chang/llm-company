from __future__ import annotations

from pathlib import Path

from llm_wiki.providers import MockProvider
from llm_wiki.refine import refine_vault
from llm_wiki.utils import markdown_with_frontmatter


def test_refine_merges_duplicate_title_pages_and_rewrites_links(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    build = tmp_path / ".wiki_build"
    vault.mkdir()
    (vault / "young-hyun-jun.md").write_text(
        markdown_with_frontmatter(
            {
                "title": "Young Hyun Jun",
                "aliases": ["Young-Hyun Jun"],
                "tags": ["leadership"],
                "source_paths": ["company/profile.md"],
                "confidence": 0.8,
            },
            "# Young Hyun Jun\n\nCEO note.",
        ),
        encoding="utf-8",
    )
    (vault / "young-hyun-jun-2.md").write_text(
        markdown_with_frontmatter(
            {
                "title": "Young Hyun Jun",
                "aliases": ["전영현"],
                "tags": ["governance"],
                "source_paths": ["company/leadership.md"],
                "confidence": 0.95,
            },
            "# Young Hyun Jun\n\nGovernance note.",
        ),
        encoding="utf-8",
    )
    (vault / "samsung-electronics.md").write_text(
        markdown_with_frontmatter(
            {"title": "Samsung Electronics", "aliases": [], "tags": [], "source_paths": []},
            "Leader: [[전영현]].",
        ),
        encoding="utf-8",
    )

    result = refine_vault(vault, build, MockProvider())

    assert result.page_count == 2
    assert result.merged_page_count == 1
    assert not (vault / "young-hyun-jun-2.md").exists()
    merged = (vault / "young-hyun-jun.md").read_text(encoding="utf-8")
    assert "전영현" in merged
    assert "company/profile.md" in merged
    assert "company/leadership.md" in merged
    assert "Mock refined page." in merged
    linked = (vault / "samsung-electronics.md").read_text(encoding="utf-8")
    assert "[[Young Hyun Jun|전영현]]" in linked
    assert (build / "reports" / "refine_report.md").exists()
