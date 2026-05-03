from __future__ import annotations

import json
import re
from pathlib import Path

from llm_wiki.utils import markdown_with_frontmatter, split_frontmatter


WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def resolve_links(vault_root: Path, build_root: Path) -> list[str]:
    index_path = build_root / "index" / "pages.json"
    if not index_path.exists():
        return []

    pages = json.loads(index_path.read_text(encoding="utf-8"))
    canonical = {}
    for page in pages:
        title = page["title"]
        for value in [title, *page.get("aliases", [])]:
            canonical[value] = title
            for variant in _lookup_variants(value):
                canonical.setdefault(variant, title)

    unresolved: set[str] = set()
    for path in vault_root.rglob("*.md"):
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))

        def replace(match: re.Match[str]) -> str:
            target = match.group(1).strip()
            canonical_target = _lookup(canonical, target)
            if not canonical_target:
                unresolved.add(target)
                return match.group(0)
            if canonical_target == target:
                return match.group(0)
            display = _display_text(match.group(0))
            if display:
                return f"[[{canonical_target}|{display}]]"
            return f"[[{canonical_target}|{target}]]"

        updated_body = WIKI_LINK_PATTERN.sub(replace, body)
        if updated_body != body:
            path.write_text(markdown_with_frontmatter(meta, updated_body), encoding="utf-8")

    report_root = build_root / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    report_path = report_root / "unresolved_links.md"
    if unresolved:
        report_path.write_text(
            "# Unresolved Links\n\n" + "\n".join(f"- [[{target}]]" for target in sorted(unresolved)) + "\n",
            encoding="utf-8",
        )
    else:
        report_path.write_text("# Unresolved Links\n\nNo unresolved links.\n", encoding="utf-8")
    return sorted(unresolved)


def _display_text(link: str) -> str:
    if "|" not in link:
        return ""
    return link.removeprefix("[[").removesuffix("]]").split("|", 1)[1].strip()


def _singularize(value: str) -> str:
    if value.endswith("Businesses"):
        return value[: -len("Businesses")] + "Business"
    if value.endswith("businesses"):
        return value[: -len("businesses")] + "business"
    return value


def _lookup(canonical: dict[str, str], target: str) -> str | None:
    for variant in _lookup_variants(target):
        if variant in canonical:
            return canonical[variant]
    return None


def _lookup_variants(value: str) -> list[str]:
    variants = [value, _singularize(value)]
    without_parens = re.sub(r"\s*\([^)]*\)", "", value).strip()
    if without_parens and without_parens != value:
        variants.append(without_parens)
    for suffix in (" Business", " Division"):
        if value.endswith(suffix):
            variants.append(value[: -len(suffix)].strip())
        else:
            variants.append(f"{value}{suffix}")
    normalized = []
    for variant in variants:
        normalized.append(variant)
        normalized.append(_normalized_key(variant))
    return list(dict.fromkeys(normalized))


def _normalized_key(value: str) -> str:
    folded = re.sub(r"\s*\([^)]*\)", "", value).strip().lower()
    folded = re.sub(r"[\s_/-]+", "-", folded)
    folded = re.sub(r"[^0-9a-z가-힣-]+", "", folded)
    return folded.strip("-")
