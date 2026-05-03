# LLM Company Wiki

Build an Obsidian-style internal wiki from a `raw/` document tree.

The pipeline is:

```text
raw/
-> preprocessed/
-> vault/
-> LLM-based vault refinement
-> reports in .wiki_build/
```

## Setup

Install dependencies:

```bash
uv sync --extra dev
```

Create `.env` from `.env.example` and set your provider credentials. The default provider is OpenAI with `gpt-5.4-mini`.

```dotenv
LLM_WIKI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
```

Optional providers:

```dotenv
LLM_WIKI_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT=...
```

```dotenv
LLM_WIKI_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.5-pro
```

## 1. Prepare `raw/`

Put source documents under `raw/` using the hierarchy you want the wiki builder to understand.

Recommended shape:

```text
raw/
  level1/
    level2/
      level3/
        document.md
        document.pdf
```

Example:

```text
raw/samsung-electronics-public/
  business/
    ds/
      memory-business.md
      foundry-and-nodes.md
    dx/
      mobile-ai.md
      networks-vran-oran.md
  company/
    profile/
      overview.md
    management/
      leadership.md
```

What to put in `raw/`:

- Markdown, text, JSON, YAML, CSV, XML
- PDFs, images, office documents, and other binary files
- Public or internal source material that should become wiki knowledge

Avoid putting generated output into `raw/`. The source tree should be the ground truth.

Hidden files such as `.DS_Store` are skipped automatically.

## 2. Preprocess

Run:

```bash
uv run llm-wiki preprocess --raw raw --out preprocessed
```

For the included Samsung example:

```bash
uv run llm-wiki preprocess \
  --raw raw/samsung-electronics-public \
  --out preprocessed/samsung-electronics-public
```

What happens:

- Every raw file is mapped to the same relative path under `preprocessed/`.
- The output extension is always `.md`.
- Text and Markdown files are read directly by default.
- If the active LLM provider supports the file MIME type, the original file is sent to the LLM and converted to Markdown.
- Unsupported MIME types fall back to docling.
- If LLM extraction fails, docling is used as fallback.
- Files with unchanged source hashes are skipped unless `--force` is used.

Each preprocessed file includes YAML frontmatter:

```yaml
source_path: business/ds/memory-business.md
source_sha256: ...
processed_at: ...
processor: direct
mime_type: text/markdown
llm_provider: openai
fallback_used: false
```

Useful options:

```bash
uv run llm-wiki preprocess --raw raw --out preprocessed --force
uv run llm-wiki preprocess --raw raw --out preprocessed --concurrency 8
uv run llm-wiki preprocess --raw raw --out preprocessed --dry-run
```

## 3. Build

Run:

```bash
uv run llm-wiki build --preprocessed preprocessed --vault vault
```

For the included Samsung example:

```bash
uv run llm-wiki build \
  --preprocessed preprocessed/samsung-electronics-public \
  --vault vault/samsung-electronics-public
```

What happens:

1. Level summaries are generated.
   - level1 summaries are generated first.
   - level2 summaries receive parent level1 context.
   - level3 summaries receive parent level1 and level2 context.
2. Each preprocessed file is converted into one or more concept pages.
   - The LLM receives the file body plus relevant hierarchy summaries.
   - It returns structured pages with `title`, `aliases`, `tags`, `concept_type`, `confidence`, and Markdown body.
3. Initial Obsidian Markdown files are written into `vault/`.
   - Duplicate names may temporarily become `concept-2.md`, `concept-3.md`.
4. LLM-based vault refinement runs automatically.
5. Links are resolved and reports are written.

Generated wiki pages include frontmatter like:

```yaml
title: Memory Business
aliases:
  - Samsung Memory Business
tags:
  - memory
  - semiconductor
source_paths:
  - business/ds/memory-business.md
concept_type: business
confidence: 0.94
```

## 4. Clean Up / Refine

`build` already runs refinement automatically. Use `refine` when you want to clean an existing vault again without rerunning preprocess or concept extraction.

```bash
uv run llm-wiki refine --vault vault/samsung-electronics-public
```

What happens:

- The vault is scanned for duplicate concept pages.
- Candidate groups are found mechanically from titles, aliases, and numeric slug variants such as `young-hyun-jun.md` and `young-hyun-jun-2.md`.
- The active LLM provider merges each duplicate group into one canonical page.
- Source paths are preserved mechanically so provenance is not lost.
- Links are rewritten to the canonical page title.
- The page index is refreshed.

Important behavior:

- Body merging is LLM-based, not deterministic string concatenation.
- If LLM refinement fails, the build should fail rather than silently producing a low-quality merge.
- Title and alias output is guarded so the model cannot freely invent new identifiers.

Reports:

```text
.wiki_build/reports/refine_report.md
.wiki_build/reports/unresolved_links.md
.wiki_build/reports/build_report.json
```

## 5. Run Everything

Use `all` for a full raw-to-vault build:

```bash
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault
```

For the included Samsung example:

```bash
rm -rf preprocessed vault .wiki_build
uv run llm-wiki all \
  --raw raw/samsung-electronics-public \
  --preprocessed preprocessed/samsung-electronics-public \
  --vault vault/samsung-electronics-public \
  --concurrency 4 \
  --force
```

The current example build produces:

```text
preprocessed/samsung-electronics-public/
vault/samsung-electronics-public/
.wiki_build/summaries/
.wiki_build/index/pages.json
.wiki_build/reports/
```

## 6. How Each Stage Works

### Preprocess internals

Preprocess is file-oriented and parallel.

- It walks `raw/`.
- It ignores hidden files.
- It detects MIME type.
- It chooses direct read, LLM extraction, or docling fallback.
- It writes Markdown with source metadata.

Path preservation example:

```text
raw/company/profile/overview.pdf
-> preprocessed/company/profile/overview.md
```

### Summary internals

Summary generation is hierarchy-oriented.

- The builder treats the first three path levels as context hierarchy.
- level1 directories are summarized in parallel.
- level2 summaries include the parent level1 summary.
- level3 summaries include parent level1 and level2 summaries.
- Summaries are stored under `.wiki_build/summaries/`.

Example:

```text
preprocessed/business/ds/memory-business.md
```

receives context from:

```text
.wiki_build/summaries/business.md
.wiki_build/summaries/business/ds.md
```

### Concept extraction internals

Concept extraction is file-oriented and parallel.

For each preprocessed file, the LLM receives:

- relevant hierarchy summaries
- source path
- Markdown body

The LLM returns structured concept pages. A single source file can produce many wiki pages.

### Refinement internals

Refinement is vault-oriented.

- It loads all generated vault pages.
- It groups likely duplicates.
- It asks the LLM to merge each duplicate group.
- It rewrites links to canonical titles.
- It regenerates `.wiki_build/index/pages.json`.

This is where pages like `young-hyun-jun.md` and `young-hyun-jun-2.md` are collapsed into one note.

### Link resolution internals

Link resolution builds a title/alias index and checks all `[[...]]` links.

- Known aliases are rewritten to canonical page titles.
- Simple variants such as plural `Businesses` -> `Business`, case differences, and suffix variants are normalized.
- Links that still cannot be matched are reported in `.wiki_build/reports/unresolved_links.md`.

## 7. Common Commands

```bash
# Full rebuild from scratch
rm -rf preprocessed vault .wiki_build
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault --force

# Re-run only preprocessing
uv run llm-wiki preprocess --raw raw --out preprocessed --force

# Re-run only wiki build from existing preprocessed files
uv run llm-wiki build --preprocessed preprocessed --vault vault

# Re-run only vault cleanup
uv run llm-wiki refine --vault vault

# Use mock provider for local structural tests
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault --provider mock
```

## 8. Git and Outputs

This repository tracks the public example raw data under:

```text
raw/samsung-electronics-public/
```

Generated outputs are ignored by git:

```text
preprocessed/
vault/
.wiki_build/
```

This keeps private or generated wiki content out of commits by default.

Use `skills/llm-wiki-builder` as the Codex-compatible Skill wrapper for this workflow.

