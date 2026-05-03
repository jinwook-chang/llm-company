from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from llm_wiki.config import WikiConfig
from llm_wiki.generate import generate_pages
from llm_wiki.providers import LlmProvider
from llm_wiki.refine import refine_vault
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
    print(f"--- Phase 1: Building folder summaries ---")
    summaries = build_summaries(preprocessed_root, build_root, provider, concurrency=concurrency)
    
    print(f"--- Phase 2: Generating wiki pages ---")
    pages = generate_pages(
        preprocessed_root,
        vault_root,
        build_root,
        provider,
        summaries,
        wiki_config,
        concurrency=concurrency,
    )
    
    print(f"--- Phase 3: Refining vault (merging duplicates) ---")
    refine_result = refine_vault(vault_root, build_root, provider)
    
    print(f"--- Phase 4: Resolving links ---")
    unresolved = resolve_links(vault_root, build_root)
    report = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "summary_count": len(summaries),
        "generated_page_count": len(pages),
        "page_count": refine_result.page_count,
        "merged_page_count": refine_result.merged_page_count,
        "rewritten_link_count": refine_result.rewritten_link_count,
        "unresolved_link_count": len(unresolved),
    }
    report_root = build_root / "reports"
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / "build_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
