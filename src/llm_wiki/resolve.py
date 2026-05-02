from __future__ import annotations

import json
import re
from pathlib import Path

from llm_wiki.utils import split_frontmatter


WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def resolve_links(vault_root: Path, build_root: Path) -> list[str]:
    index_path = build_root / "index" / "pages.json"
    if not index_path.exists():
        return []

    pages = json.loads(index_path.read_text(encoding="utf-8"))
    known = {page["title"] for page in pages}
    for page in pages:
        known.update(page.get("aliases", []))

    unresolved: set[str] = set()
    for path in vault_root.rglob("*.md"):
        _, body = split_frontmatter(path.read_text(encoding="utf-8"))
        for match in WIKI_LINK_PATTERN.finditer(body):
            target = match.group(1).strip()
            if target not in known:
                unresolved.add(target)

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

