from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from llm_wiki.config import WikiConfig
from llm_wiki.generate import generate_pages
from llm_wiki.providers import LlmProvider
from llm_wiki.resolve import resolve_links
from llm_wiki.summarize import build_summaries


def build_wiki(
    preprocessed_root: Path,
    vault_root: Path,
    build_root: Path,
    provider: LlmProvider,
    wiki_config: WikiConfig,
    *,
    concurrency: int = 4,
) -> dict:
    summaries = build_summaries(preprocessed_root, build_root, provider, concurrency=concurrency)
    pages = generate_pages(
        preprocessed_root,
        vault_root,
        build_root,
        provider,
        summaries,
        wiki_config,
        concurrency=concurrency,
    )
    unresolved = resolve_links(vault_root, build_root)
    report = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "summary_count": len(summaries),
        "page_count": len(pages),
        "unresolved_link_count": len(unresolved),
    }
    report_root = build_root / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

