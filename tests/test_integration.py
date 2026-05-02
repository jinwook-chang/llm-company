from __future__ import annotations

from pathlib import Path

from llm_wiki.build import build_wiki
from llm_wiki.config import PreprocessConfig, WikiConfig
from llm_wiki.preprocess import preprocess_tree
from llm_wiki.providers import MockProvider


def test_mock_all_pipeline(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    source = raw / "product" / "platform" / "search" / "overview.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Search Platform\n\nSearch uses ranking signals.", encoding="utf-8")

    preprocessed = tmp_path / "preprocessed"
    vault = tmp_path / "vault"
    build = tmp_path / ".wiki_build"
    provider = MockProvider()

    preprocess_results = preprocess_tree(raw, preprocessed, provider, PreprocessConfig(), concurrency=2)
    report = build_wiki(preprocessed, vault, build, provider, WikiConfig(), concurrency=2)

    assert len(preprocess_results) == 1
    assert (preprocessed / "product" / "platform" / "search" / "overview.md").exists()
    assert report["page_count"] == 1
    assert list(vault.glob("*.md"))
    assert (build / "summaries" / "product.md").exists()
    assert (build / "index" / "pages.json").exists()
    assert (build / "reports" / "unresolved_links.md").exists()

