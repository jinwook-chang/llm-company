from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_wiki.providers import LlmProvider
from llm_wiki.resolve import WIKI_LINK_PATTERN
from llm_wiki.schemas import ConceptPage
from llm_wiki.utils import markdown_with_frontmatter, normalize_tag, slugify, split_frontmatter


REFINE_SYSTEM_PROMPT = """Merge duplicate Obsidian wiki pages into one canonical page.

Rules:
- Preserve all factual information and do not invent facts.
- Choose the clearest canonical title.
- Put alternate spellings, Korean names, acronyms, and prior titles into aliases.
- Merge overlapping content without repeating identical facts.
- Keep useful Obsidian links.
- Return one polished page body in Markdown.
"""


@dataclass
class RefineResult:
    page_count: int
    merged_page_count: int
    rewritten_link_count: int


@dataclass
class VaultPage:
    path: Path
    meta: dict[str, Any]
    body: str

    @property
    def title(self) -> str:
        return str(self.meta.get("title") or self.path.stem)

    @property
    def aliases(self) -> list[str]:
        aliases = self.meta.get("aliases") or []
        return [str(alias) for alias in aliases]


def refine_vault(vault_root: Path, build_root: Path, provider: LlmProvider) -> RefineResult:
    pages = _load_pages(vault_root)
    if not pages:
        _write_refine_report(build_root, [], 0, 0)
        _write_page_index(build_root, [], vault_root)
        return RefineResult(page_count=0, merged_page_count=0, rewritten_link_count=0)

    groups = _group_pages(pages)
    merged_pages: list[VaultPage] = []
    merged_titles: list[str] = []
    alias_to_title: dict[str, str] = {}
    used_paths: set[Path] = set()

    for group in groups:
        canonical = _choose_canonical(group)
        merged = _merge_group(group, canonical, provider)
        canonical_path = _unique_page_path(vault_root, merged.title, used_paths)
        used_paths.add(canonical_path)
        if len(group) > 1:
            merged_titles.append(merged.title)
        merged.path = canonical_path
        merged_pages.append(merged)
        for value in [merged.title, *merged.aliases, *[page.title for page in group], *sum([page.aliases for page in group], [])]:
            alias_to_title[value] = merged.title

    _replace_vault_pages(vault_root, merged_pages)
    rewritten = _rewrite_links(vault_root, alias_to_title)
    _write_page_index(build_root, merged_pages, vault_root)
    _write_refine_report(build_root, merged_titles, len(merged_pages), rewritten)
    return RefineResult(
        page_count=len(merged_pages),
        merged_page_count=len(merged_titles),
        rewritten_link_count=rewritten,
    )


def _load_pages(vault_root: Path) -> list[VaultPage]:
    pages: list[VaultPage] = []
    for path in sorted(vault_root.rglob("*.md")):
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("title"):
            pages.append(VaultPage(path=path, meta=meta, body=body))
    return pages


def _group_pages(pages: list[VaultPage]) -> list[list[VaultPage]]:
    parent = {page.path: page.path for page in pages}
    by_key: dict[str, Path] = {}

    def find(path: Path) -> Path:
        while parent[path] != path:
            parent[path] = parent[parent[path]]
            path = parent[path]
        return path

    def union(left: Path, right: Path) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for page in pages:
        keys = _page_keys(page)
        for key in keys:
            if key in by_key:
                union(page.path, by_key[key])
            else:
                by_key[key] = page.path

    grouped: dict[Path, list[VaultPage]] = {}
    for page in pages:
        grouped.setdefault(find(page.path), []).append(page)
    return sorted(grouped.values(), key=lambda group: _choose_canonical(group).title.lower())


def _page_keys(page: VaultPage) -> set[str]:
    keys = {_normalized_key(page.title), _normalized_key(_strip_numeric_suffix(page.path.stem))}
    keys.update(_normalized_key(alias) for alias in page.aliases)
    return {key for key in keys if key}


def _choose_canonical(group: list[VaultPage]) -> VaultPage:
    return sorted(group, key=_canonical_sort_key)[0]


def _canonical_sort_key(page: VaultPage) -> tuple[int, float, int, str]:
    suffix_penalty = 1 if re.search(r"-\d+$", page.path.stem) else 0
    confidence = float(page.meta.get("confidence") or 0.0)
    return (suffix_penalty, -confidence, len(page.title), page.title.lower())


def _merge_group(group: list[VaultPage], canonical: VaultPage, provider: LlmProvider) -> VaultPage:
    aliases = _dedupe(
        [
            *canonical.aliases,
            *[page.title for page in group if page.title != canonical.title],
            *sum([page.aliases for page in group if page.path != canonical.path], []),
        ]
    )
    tags = sorted(
        {
            normalize_tag(str(tag))
            for page in group
            for tag in (page.meta.get("tags") or [])
            if str(tag).strip()
        }
    )
    source_paths = _dedupe(
        [
            str(source)
            for page in group
            for source in (page.meta.get("source_paths") or [page.meta.get("source_path") or ""])
            if str(source).strip()
        ]
    )
    llm_page = _llm_merge_group(group, canonical, provider) if len(group) > 1 else None
    body = llm_page.body if llm_page else canonical.body
    confidence = max(float(page.meta.get("confidence") or 0.0) for page in group)
    title_candidates = _dedupe([page.title for page in group] + sum([page.aliases for page in group], []))
    title = _validated_title(llm_page.title, title_candidates, canonical.title) if llm_page else canonical.title
    if llm_page:
        aliases = _dedupe([*aliases, canonical.title])
        tags = sorted({normalize_tag(tag) for tag in [*llm_page.tags, *tags] if tag.strip()})
        confidence = max(confidence, llm_page.confidence)
    meta = {
        **canonical.meta,
        "title": title,
        "aliases": aliases,
        "tags": tags,
        "source_paths": source_paths,
        "confidence": confidence,
    }
    return VaultPage(path=canonical.path, meta=meta, body=body)


def _llm_merge_group(group: list[VaultPage], canonical: VaultPage, provider: LlmProvider) -> ConceptPage:
    payload = []
    for page in group:
        payload.append(
            "\n".join(
                [
                    f"# Page: {page.title}",
                    f"Aliases: {', '.join(page.aliases)}",
                    f"Tags: {', '.join(str(tag) for tag in page.meta.get('tags', []))}",
                    f"Sources: {', '.join(str(source) for source in page.meta.get('source_paths', []))}",
                    "",
                    page.body[:12000],
                ]
            )
        )
    return provider.generate_structured(
        REFINE_SYSTEM_PROMPT,
        [
            {
                "role": "user",
                "content": (
                    f"Canonical seed title: {canonical.title}\n\n"
                    "Merge these duplicate pages into one canonical Obsidian page:\n\n"
                    + "\n\n---\n\n".join(payload)
                ),
            }
        ],
        ConceptPage,
    )


def _unique_page_path(vault_root: Path, title: str, used_paths: set[Path]) -> Path:
    base = slugify(title)
    path = vault_root / f"{base}.md"
    counter = 2
    while path in used_paths:
        path = vault_root / f"{base}-{counter}.md"
        counter += 1
    return path


def _replace_vault_pages(vault_root: Path, pages: list[VaultPage]) -> None:
    for path in vault_root.rglob("*.md"):
        path.unlink()
    for page in pages:
        page.path.parent.mkdir(parents=True, exist_ok=True)
        page.path.write_text(markdown_with_frontmatter(page.meta, page.body), encoding="utf-8")


def _rewrite_links(vault_root: Path, alias_to_title: dict[str, str]) -> int:
    rewritten = 0
    for path in vault_root.rglob("*.md"):
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))

        def replace(match: re.Match[str]) -> str:
            nonlocal rewritten
            target = match.group(1).strip()
            canonical = alias_to_title.get(target)
            if not canonical or canonical == target:
                return match.group(0)
            rewritten += 1
            display = _display_text(match.group(0)) or target
            return f"[[{canonical}|{display}]]"

        updated_body = WIKI_LINK_PATTERN.sub(replace, body)
        if updated_body != body:
            path.write_text(markdown_with_frontmatter(meta, updated_body), encoding="utf-8")
    return rewritten


def _write_page_index(build_root: Path, pages: list[VaultPage], vault_root: Path) -> None:
    index_root = build_root / "index"
    index_root.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "title": page.title,
            "path": str(page.path.relative_to(vault_root)),
            "aliases": page.aliases,
            "tags": page.meta.get("tags", []),
            "source_paths": page.meta.get("source_paths", []),
        }
        for page in sorted(pages, key=lambda item: item.title.lower())
    ]
    (index_root / "pages.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_refine_report(build_root: Path, merged_titles: list[str], page_count: int, rewritten: int) -> None:
    report_root = build_root / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    body = [
        "# Vault Refinement",
        "",
        f"- Pages after refinement: {page_count}",
        f"- Merged page groups: {len(merged_titles)}",
        f"- Rewritten links: {rewritten}",
        "",
        "## Merged Pages",
        "",
    ]
    if merged_titles:
        body.extend(f"- [[{title}]]" for title in sorted(merged_titles))
    else:
        body.append("No duplicate pages were merged.")
    (report_root / "refine_report.md").write_text("\n".join(body) + "\n", encoding="utf-8")


def _normalized_key(value: str) -> str:
    return slugify(value).lower()


def _strip_numeric_suffix(value: str) -> str:
    return re.sub(r"-\d+$", "", value)


def _display_text(link: str) -> str:
    if "|" not in link:
        return ""
    return link.removeprefix("[[").removesuffix("]]").split("|", 1)[1].strip()


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _validated_title(candidate: str, allowed: list[str], fallback: str) -> str:
    allowed_by_key = {}
    for value in allowed:
        allowed_by_key.setdefault(_normalized_key(value), value)
    return allowed_by_key.get(_normalized_key(candidate), fallback)
