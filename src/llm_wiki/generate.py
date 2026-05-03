from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from llm_wiki.config import WikiConfig
from llm_wiki.providers import LlmProvider
from llm_wiki.schemas import ConceptPage, ConceptPagesResult, SummaryResult
from llm_wiki.summarize import relevant_context
from llm_wiki.utils import markdown_with_frontmatter, normalize_tag, slugify, split_frontmatter


GENERATE_SYSTEM_PROMPT = """Create Obsidian wiki concept pages from internal company documents.

Rules:
- Extract multiple concept pages when the source contains multiple important concepts.
- Preserve source facts. Do not invent.
- Write in the same primary language as the source.
- Use Obsidian links like [[Concept]] only for concepts that should become pages.
- Include concise tags.
"""


@dataclass(frozen=True)
class GeneratedPage:
    title: str
    path: Path
    aliases: list[str]
    tags: list[str]
    source_path: str


def generate_pages(
    preprocessed_root: Path,
    vault_root: Path,
    build_root: Path,
    provider: LlmProvider,
    summaries: dict[Path, SummaryResult],
    wiki_config: WikiConfig,
    *,
    concurrency: int = 4,
) -> list[GeneratedPage]:
    files = sorted(preprocessed_root.rglob("*.md"))
    page_root = vault_root / wiki_config.page_dir
    page_root.mkdir(parents=True, exist_ok=True)
    _clear_existing_pages(page_root)
    used_slugs: set[str] = set()
    generated: list[GeneratedPage] = []

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(_extract_pages, path, preprocessed_root, provider, summaries): path
            for path in files
        }
        for future in as_completed(futures):
            source_path = futures[future]
            relative = source_path.relative_to(preprocessed_root)
            meta, source_body = split_frontmatter(source_path.read_text(encoding="utf-8"))
            for page in future.result():
                slug = _unique_slug(slugify(page.title), used_slugs)
                aliases = _safe_aliases(page.title, page.aliases, source_body)
                tags = sorted({normalize_tag(tag, wiki_config.tag_prefix) for tag in page.tags if tag.strip()})
                output_path = page_root / f"{slug}.md"
                output_path.write_text(
                    markdown_with_frontmatter(
                        {
                            "title": page.title,
                            "aliases": aliases,
                            "tags": tags,
                            "source_paths": [meta.get("source_path", str(relative))],
                            "concept_type": page.concept_type,
                            "confidence": page.confidence,
                        },
                        page.body,
                    ),
                    encoding="utf-8",
                )
                generated.append(
                    GeneratedPage(
                        title=page.title,
                        path=output_path,
                        aliases=aliases,
                        tags=tags,
                        source_path=str(relative),
                    )
            )

    write_page_index(build_root, generated, vault_root)
    return sorted(generated, key=lambda page: page.title)


def write_page_index(build_root: Path, pages: list[GeneratedPage], vault_root: Path) -> None:
    import json

    index_root = build_root / "index"
    index_root.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "title": page.title,
            "path": str(page.path.relative_to(vault_root)),
            "aliases": page.aliases,
            "tags": page.tags,
            "source_path": page.source_path,
        }
        for page in pages
    ]
    (index_root / "pages.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_pages(
    path: Path,
    preprocessed_root: Path,
    provider: LlmProvider,
    summaries: dict[Path, SummaryResult],
) -> list[ConceptPage]:
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    relative = path.relative_to(preprocessed_root)
    context = relevant_context(relative, summaries)
    result = provider.generate_structured(
        GENERATE_SYSTEM_PROMPT,
        [
            {
                "role": "user",
                "content": f"{context}\n\n# Source: {meta.get('source_path', relative)}\n\n{body[:50000]}",
            }
        ],
        ConceptPagesResult,
    )
    return result.pages


def _unique_slug(base: str, used: set[str]) -> str:
    slug = base
    counter = 2
    while slug in used:
        slug = f"{base}-{counter}"
        counter += 1
    used.add(slug)
    return slug


def _clear_existing_pages(page_root: Path) -> None:
    for path in page_root.glob("*.md"):
        path.unlink()


def _safe_aliases(title: str, aliases: list[str], source_body: str) -> list[str]:
    title_key = slugify(title)
    safe: list[str] = []
    for alias in aliases:
        value = alias.strip()
        if not value:
            continue
        if value in source_body or slugify(value) == title_key:
            safe.append(value)
    return list(dict.fromkeys(safe))
