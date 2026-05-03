from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm_wiki.build import build_wiki
from llm_wiki.config import load_config
from llm_wiki.preprocess import preprocess_tree
from llm_wiki.providers import make_provider
from llm_wiki.refine import refine_vault
from llm_wiki.resolve import resolve_links


def main() -> None:
    parser = argparse.ArgumentParser(prog="llm-wiki")
    parser.add_argument("--config", default="wiki.config.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preprocess_parser = subparsers.add_parser("preprocess")
    preprocess_parser.add_argument("--raw", type=Path)
    preprocess_parser.add_argument("--out", type=Path)
    _add_common(preprocess_parser)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--preprocessed", type=Path)
    build_parser.add_argument("--vault", type=Path)
    _add_common(build_parser)

    refine_parser = subparsers.add_parser("refine")
    refine_parser.add_argument("--vault", type=Path)
    refine_parser.add_argument("--build-root", type=Path)
    refine_parser.add_argument("--provider", choices=["mock", "openai", "azure_openai", "vertex"])

    all_parser = subparsers.add_parser("all")
    all_parser.add_argument("--raw", type=Path)
    all_parser.add_argument("--preprocessed", type=Path)
    all_parser.add_argument("--vault", type=Path)
    _add_common(all_parser)

    args = parser.parse_args()
    config = load_config(args.config)

    if args.command == "preprocess":
        provider_name = args.provider or config.llm.provider
        provider = make_provider(provider_name, config.llm.model, config.mime_overrides)
        concurrency = args.concurrency or config.llm.concurrency
        results = preprocess_tree(
            args.raw or config.paths.raw,
            args.out or config.paths.preprocessed,
            provider,
            config.preprocess,
            concurrency=concurrency,
            force=args.force,
            dry_run=args.dry_run,
        )
        _print_preprocess_results(results)
        return

    if args.command == "build":
        provider_name = args.provider or config.llm.provider
        provider = make_provider(provider_name, config.llm.model, config.mime_overrides)
        concurrency = args.concurrency or config.llm.concurrency
        report = build_wiki(
            args.preprocessed or config.paths.preprocessed,
            args.vault or config.paths.vault,
            config.paths.build,
            provider,
            config.wiki,
            concurrency=concurrency,
        )
        _print_report(report)
        return

    if args.command == "refine":
        vault_root = args.vault or config.paths.vault
        build_root = args.build_root or config.paths.build
        provider_name = args.provider or config.llm.provider
        provider = make_provider(provider_name, config.llm.model, config.mime_overrides)
        refine_result = refine_vault(vault_root, build_root, provider)
        unresolved = resolve_links(vault_root, build_root)
        _update_refine_report(build_root, refine_result, len(unresolved))
        print(
            "refine: "
            f"pages={refine_result.page_count} "
            f"merged={refine_result.merged_page_count} "
            f"rewritten_links={refine_result.rewritten_link_count} "
            f"unresolved_links={len(unresolved)}"
        )
        return

    if args.command == "all":
        provider_name = args.provider or config.llm.provider
        provider = make_provider(provider_name, config.llm.model, config.mime_overrides)
        concurrency = args.concurrency or config.llm.concurrency
        preprocess_results = preprocess_tree(
            args.raw or config.paths.raw,
            args.preprocessed or config.paths.preprocessed,
            provider,
            config.preprocess,
            concurrency=concurrency,
            force=args.force,
            dry_run=args.dry_run,
        )
        _print_preprocess_results(preprocess_results)
        if args.dry_run:
            return
        report = build_wiki(
            args.preprocessed or config.paths.preprocessed,
            args.vault or config.paths.vault,
            config.paths.build,
            provider,
            config.wiki,
            concurrency=concurrency,
        )
        _print_report(report)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", choices=["mock", "openai", "azure_openai", "vertex"])
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")


def _print_preprocess_results(results: list) -> None:
    processed = len([result for result in results if not result.skipped])
    skipped = len([result for result in results if result.skipped])
    fallback = len([result for result in results if result.fallback_used])
    print(f"preprocess: processed={processed} skipped={skipped} fallback={fallback}")
    for result in results:
        status = "skipped" if result.skipped else "processed"
        print(f"- {status}: {result.source_path} -> {result.output_path} ({result.processor})")


def _print_report(report: dict) -> None:
    print(
        "build: "
        f"summaries={report['summary_count']} "
        f"pages={report['page_count']} "
        f"merged={report.get('merged_page_count', 0)} "
        f"unresolved_links={report['unresolved_link_count']}"
    )


def _update_refine_report(build_root: Path, refine_result, unresolved_count: int) -> None:
    report_path = build_root / "reports" / "build_report.json"
    if not report_path.exists():
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["page_count"] = refine_result.page_count
    report["merged_page_count"] = refine_result.merged_page_count
    report["rewritten_link_count"] = refine_result.rewritten_link_count
    report["unresolved_link_count"] = unresolved_count
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
