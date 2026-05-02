from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from llm_wiki.config import PreprocessConfig
from llm_wiki.mime import detect_mime, is_text_mime
from llm_wiki.providers import LlmProvider
from llm_wiki.utils import ensure_relative, markdown_with_frontmatter, sha256_file, split_frontmatter


@dataclass(frozen=True)
class PreprocessResult:
    source_path: Path
    output_path: Path
    processor: str
    skipped: bool
    fallback_used: bool


EXTRACT_PROMPT = """Extract the attached company document as clean Markdown.

Rules:
- Preserve headings, tables, lists, definitions, and important labels.
- Do not summarize.
- Do not invent facts.
- If the document contains Korean text, keep Korean text in Korean.
- Return only Markdown.
"""


def preprocess_tree(
    raw_root: Path,
    out_root: Path,
    provider: LlmProvider,
    config: PreprocessConfig,
    *,
    concurrency: int = 4,
    force: bool = False,
    dry_run: bool = False,
) -> list[PreprocessResult]:
    files = [path for path in sorted(raw_root.rglob("*")) if path.is_file()]
    out_root.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return [
            PreprocessResult(path, output_path_for(path, raw_root, out_root), "dry-run", False, False)
            for path in files
        ]

    results: list[PreprocessResult] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [
            executor.submit(preprocess_file, path, raw_root, out_root, provider, config, force=force)
            for path in files
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda result: str(result.source_path))


def preprocess_file(
    source_path: Path,
    raw_root: Path,
    out_root: Path,
    provider: LlmProvider,
    config: PreprocessConfig,
    *,
    force: bool = False,
) -> PreprocessResult:
    source_hash = sha256_file(source_path)
    output_path = output_path_for(source_path, raw_root, out_root)
    if not force and _already_current(output_path, source_hash):
        meta, _ = split_frontmatter(output_path.read_text(encoding="utf-8"))
        return PreprocessResult(
            source_path,
            output_path,
            str(meta.get("processor", "unknown")),
            skipped=True,
            fallback_used=bool(meta.get("fallback_used", False)),
        )

    mime_type = detect_mime(source_path)
    fallback_used = False
    processor = "direct"

    if is_text_mime(mime_type) and config.text_strategy == "direct":
        body = _read_text_as_markdown(source_path, mime_type)
    elif provider.supports_mime(mime_type):
        try:
            extracted = provider.extract_markdown_from_file(source_path, mime_type, EXTRACT_PROMPT)
            body = extracted.markdown
            processor = extracted.processor
        except Exception:
            body = docling_to_markdown(source_path)
            processor = "docling"
            fallback_used = True
    else:
        body = docling_to_markdown(source_path)
        processor = "docling"
        fallback_used = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        markdown_with_frontmatter(
            {
                "source_path": str(ensure_relative(source_path, raw_root)),
                "source_sha256": source_hash,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processor": processor,
                "mime_type": mime_type,
                "llm_provider": provider.name,
                "fallback_used": fallback_used,
            },
            body,
        ),
        encoding="utf-8",
    )
    return PreprocessResult(source_path, output_path, processor, skipped=False, fallback_used=fallback_used)


def output_path_for(source_path: Path, raw_root: Path, out_root: Path) -> Path:
    relative = ensure_relative(source_path, raw_root)
    return out_root / relative.with_suffix(".md")


def docling_to_markdown(path: Path) -> str:
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise RuntimeError(
            "docling is required for unsupported MIME types. Install with `uv sync --extra docling`."
        ) from exc

    converter = DocumentConverter()
    result = converter.convert(path)
    return result.document.export_to_markdown()


def _already_current(output_path: Path, source_hash: str) -> bool:
    if not output_path.exists():
        return False
    meta, _ = split_frontmatter(output_path.read_text(encoding="utf-8"))
    return meta.get("source_sha256") == source_hash


def _read_text_as_markdown(path: Path, mime_type: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if mime_type == "text/markdown" or path.suffix.lower() in {".md", ".markdown"}:
        return text
    return f"# {path.stem}\n\n```{_fence_language(path)}\n{text.rstrip()}\n```"


def _fence_language(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".csv": "csv",
        ".xml": "xml",
        ".txt": "",
    }.get(suffix, "")

