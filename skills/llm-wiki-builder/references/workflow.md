# LLM Wiki Builder Workflow

## Preprocess Policy

The preprocess stage maps each raw file to the same relative path under `preprocessed/` with a `.md` extension.

Default routing:

- Text and Markdown files use deterministic direct reading.
- MIME types supported by the active provider are sent to the LLM for Markdown extraction.
- Unsupported MIME types use docling.
- LLM extraction failures also fall back to docling.

Each preprocessed file includes frontmatter:

- `source_path`
- `source_sha256`
- `processed_at`
- `processor`
- `mime_type`
- `llm_provider`
- `fallback_used`

## Provider Configuration

Use `.env`; never put credentials in tracked files.

OpenAI:

```dotenv
LLM_WIKI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
```

Azure OpenAI:

```dotenv
LLM_WIKI_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT=...
```

Vertex AI:

```dotenv
LLM_WIKI_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.5-pro
```

## Build Order

1. Generate level1 summaries in parallel.
2. Generate level2 summaries with parent level1 context.
3. Generate level3 summaries with parent level1 and level2 context.
4. Generate concept pages from each preprocessed file with the nearest hierarchy context.
5. Run LLM-based vault refinement over generated pages.
6. Build the page index and unresolved-link report.

## Vault Refinement

After initial page generation, the CLI scans the vault for duplicate concept pages. Candidate grouping is mechanical, but the actual merge is performed by the active LLM provider.

The refinement step:

- merges pages with the same title, alias, or numeric slug variants such as `concept.md` and `concept-2.md`
- asks the LLM to choose the canonical title, tags, aliases, and merged body from the candidate pages
- preserves `source_paths` mechanically so provenance is not lost
- rewrites links to the canonical page title
- writes `.wiki_build/reports/refine_report.md`

The implementation intentionally avoids deterministic body merging. If LLM refinement fails, the build should fail rather than silently producing a lower-quality merge.

## Obsidian Page Rules

Each generated page should include YAML frontmatter:

- `title`
- `aliases`
- `tags`
- `source_paths`
- `concept_type`
- `confidence`

Use `[[Page Title]]` or `[[Page Title|display text]]` for internal references. Tags should be lowercase, deduplicated, and whitespace-normalized.
