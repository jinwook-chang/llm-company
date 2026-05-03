from __future__ import annotations

from pathlib import Path

from llm_wiki.providers import MockProvider
from llm_wiki.summarize import build_summaries, relevant_context
from llm_wiki.utils import markdown_with_frontmatter


def test_build_summaries_supports_deep_hierarchies(tmp_path: Path) -> None:
    preprocessed = tmp_path / "preprocessed"
    source = preprocessed / "l1" / "l2" / "l3" / "l4" / "l5" / "doc.md"
    source.parent.mkdir(parents=True)
    source.write_text(markdown_with_frontmatter({"source_path": "doc.md"}, "# Deep Doc"), encoding="utf-8")

    summaries = build_summaries(preprocessed, tmp_path / ".wiki_build", MockProvider(), concurrency=2)

    assert Path("l1") in summaries
    assert Path("l1/l2/l3/l4/l5") in summaries
    assert (tmp_path / ".wiki_build" / "summaries" / "l1" / "l2" / "l3" / "l4" / "l5.md").exists()

    context = relevant_context(Path("l1/l2/l3/l4/l5/doc.md"), summaries)
    assert "## Context: l1/l2/l3/l4" in context
    assert "## Context: l1/l2/l3/l4/l5" in context

