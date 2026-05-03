from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from llm_wiki.providers import LlmProvider
from llm_wiki.schemas import SummaryResult
from llm_wiki.utils import split_frontmatter


SUMMARY_SYSTEM_PROMPT = """You summarize internal company knowledge for a hierarchical LLM wiki.

Return concise but information-dense summaries. Preserve project names, product names,
policies, decisions, owners, dates, and domain vocabulary.
"""


def build_summaries(
    preprocessed_root: Path,
    build_root: Path,
    provider: LlmProvider,
    *,
    concurrency: int = 4,
) -> dict[Path, SummaryResult]:
    summary_root = build_root / "summaries"
    summary_root.mkdir(parents=True, exist_ok=True)
    summaries: dict[Path, SummaryResult] = {}

    max_depth = _max_dir_depth(preprocessed_root)
    for depth in range(1, max_depth + 1):
        dirs = _dirs_at_depth(preprocessed_root, depth)
        summaries.update(_summarize_dirs(dirs, preprocessed_root, summary_root, provider, summaries, concurrency))

    return summaries


def relevant_context(relative_file: Path, summaries: dict[Path, SummaryResult]) -> str:
    parts: list[str] = []
    parents = list(relative_file.parents)
    for parent in reversed(parents):
        if str(parent) == ".":
            continue
        summary = summaries.get(parent)
        if summary:
            parts.append(f"## Context: {parent}\n{summary.summary}")
    return "\n\n".join(parts)


def _summarize_dirs(
    dirs: list[Path],
    root: Path,
    summary_root: Path,
    provider: LlmProvider,
    previous: dict[Path, SummaryResult],
    concurrency: int,
) -> dict[Path, SummaryResult]:
    from tqdm import tqdm

    results: dict[Path, SummaryResult] = {}
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(_summarize_dir, directory, root, summary_root, provider, previous): directory
            for directory in dirs
        }
        with tqdm(total=len(futures), desc="Summarizing folders", unit="folder") as pbar:
            for future in as_completed(futures):
                relative, result = future.result()
                results[relative] = result
                pbar.update(1)
    return results


def _summarize_dir(
    directory: Path,
    root: Path,
    summary_root: Path,
    provider: LlmProvider,
    previous: dict[Path, SummaryResult],
) -> tuple[Path, SummaryResult]:
    relative = directory.relative_to(root)
    docs = []
    for file_path in sorted(directory.rglob("*.md")):
        _, body = split_frontmatter(file_path.read_text(encoding="utf-8"))
        docs.append(f"# Source: {file_path.relative_to(root)}\n\n{body[:12000]}")

    parent_context = []
    for parent in reversed(list(relative.parents)):
        if str(parent) == ".":
            continue
        if parent in previous:
            parent_context.append(f"## Parent summary: {parent}\n{previous[parent].summary}")

    result = provider.generate_structured(
        SUMMARY_SYSTEM_PROMPT,
        [{"role": "user", "content": "\n\n".join(parent_context + docs)}],
        SummaryResult,
    )
    output_path = summary_root / relative.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"# Summary: {relative}\n\n{result.summary}\n", encoding="utf-8")
    return relative, result


def _dirs_at_depth(root: Path, depth: int) -> list[Path]:
    if not root.exists():
        return []
    dirs = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() and len(path.relative_to(root).parts) == depth:
            dirs.append(path)
    return dirs


def _max_dir_depth(root: Path) -> int:
    if not root.exists():
        return 0
    return max((len(path.relative_to(root).parts) for path in root.rglob("*") if path.is_dir()), default=0)
