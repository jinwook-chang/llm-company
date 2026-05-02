# LLM Company Wiki

Build an Obsidian-style internal wiki from a `raw/` document tree.

```bash
uv sync --extra dev
uv run llm-wiki preprocess --raw raw --out preprocessed --provider mock
uv run llm-wiki build --preprocessed preprocessed --vault vault --provider mock
uv run llm-wiki all --raw raw --preprocessed preprocessed --vault vault --provider mock
```

Use `skills/llm-wiki-builder` as the Codex-compatible Skill wrapper for the workflow.

