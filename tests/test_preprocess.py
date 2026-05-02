from __future__ import annotations

from pathlib import Path

import pytest

from llm_wiki.config import PreprocessConfig
from llm_wiki.preprocess import output_path_for, preprocess_file
from llm_wiki.preprocess import preprocess_tree
from llm_wiki.providers import LlmProvider, MarkdownResult, MockProvider


def test_output_path_preserves_tree(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    source = raw / "level1" / "level2" / "level3" / "doc.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"pdf")

    assert output_path_for(source, raw, tmp_path / "preprocessed") == (
        tmp_path / "preprocessed" / "level1" / "level2" / "level3" / "doc.md"
    )


def test_text_files_use_direct_reader_by_default(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    source = raw / "team" / "note.txt"
    source.parent.mkdir(parents=True)
    source.write_text("hello", encoding="utf-8")

    result = preprocess_file(source, raw, tmp_path / "preprocessed", MockProvider(), PreprocessConfig())

    assert result.processor == "direct"
    assert result.fallback_used is False
    assert "```" in result.output_path.read_text(encoding="utf-8")


def test_supported_mime_uses_llm(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    source = raw / "team" / "deck.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4")

    result = preprocess_file(source, raw, tmp_path / "preprocessed", MockProvider(), PreprocessConfig())

    assert result.processor == "llm:mock"
    assert result.fallback_used is False
    assert "Mock Markdown extracted" in result.output_path.read_text(encoding="utf-8")


def test_preprocess_tree_skips_hidden_system_files(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / ".DS_Store").write_bytes(b"binary")
    (raw / "visible.md").write_text("# Visible", encoding="utf-8")

    results = preprocess_tree(raw, tmp_path / "preprocessed", MockProvider(), PreprocessConfig())

    assert [result.source_path.name for result in results] == ["visible.md"]


def test_llm_failure_falls_back_to_docling(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FailingProvider(LlmProvider):
        name = "mock"

        def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
            raise RuntimeError("upload failed")

    raw = tmp_path / "raw"
    source = raw / "team" / "deck.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr("llm_wiki.preprocess.docling_to_markdown", lambda path: "# Fallback")

    result = preprocess_file(source, raw, tmp_path / "preprocessed", FailingProvider(), PreprocessConfig())

    assert result.processor == "docling"
    assert result.fallback_used is True
    assert "# Fallback" in result.output_path.read_text(encoding="utf-8")
