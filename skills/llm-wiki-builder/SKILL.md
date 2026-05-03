---
name: llm-wiki-builder
description: Build an Obsidian-style internal LLM wiki from raw company files. Use when Codex needs to preprocess raw documents, extract Markdown with OpenAI/Azure OpenAI/Vertex or docling fallback, create hierarchical summaries, generate concept pages, tags, and Obsidian links, or run the llm-wiki uv CLI.
---

# LLM Wiki Builder

## Overview

Use this skill to turn a `raw/` company document tree into an Obsidian-compatible vault. The repository provides the `llm-wiki` CLI; prefer running the CLI over recreating the workflow manually.

Read `references/workflow.md` when you need the full build sequence or troubleshooting details.

## Quick Start

From the project root:

```bash
uv sync --extra dev
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault
```

Use these focused commands when resuming a partial run:

```bash
uv run llm-wiki preprocess --raw raw --out preprocessed
uv run llm-wiki build --preprocessed preprocessed --vault vault
```

## Workflow

1. Confirm `.env` contains the intended provider credentials. Default provider is OpenAI; use `LLM_WIKI_PROVIDER=azure_openai` or `LLM_WIKI_PROVIDER=vertex` only when requested.
2. Put source material under `raw/<level1>/<level2>/<level3>/...`.
3. Run preprocess. Text and Markdown are read directly by default; provider-supported binary MIME types are sent to the LLM for Markdown extraction; unsupported or failed files fall back to docling.
4. Run build. The CLI creates level summaries, extracts concept pages, writes Obsidian Markdown, and reports unresolved links.
5. Build automatically runs LLM-based vault refinement to merge duplicate concept pages, rewrite links, and refresh the page index.
6. Inspect `.wiki_build/reports/build_report.json`, `.wiki_build/reports/refine_report.md`, and `.wiki_build/reports/unresolved_links.md`.

## Outputs

- `preprocessed/**/*.md`: Markdown versions of raw files with source frontmatter.
- `.wiki_build/summaries/**/*.md`: hierarchical summaries.
- `.wiki_build/index/pages.json`: generated page index.
- `vault/**/*.md`: final Obsidian pages.
- `.wiki_build/reports/*.md|json`: build reports.

## Operating Notes

- Do not print secrets from `.env`.
- Preserve raw file tree structure in `preprocessed/`.
- Prefer `--concurrency 1` while debugging provider issues; raise it for production runs.
- Use `--force` to reprocess unchanged files.
- Use `--provider mock` only for local debugging when real API calls are not desired.
- Use `uv run llm-wiki refine --vault <vault>` to rerun only the LLM-based vault cleanup step.
