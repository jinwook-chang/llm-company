from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

ProviderName = Literal["mock", "openai", "azure_openai", "vertex"]


@dataclass(frozen=True)
class PathConfig:
    raw: Path = Path("raw")
    preprocessed: Path = Path("preprocessed")
    vault: Path = Path("vault")
    build: Path = Path(".wiki_build")


@dataclass(frozen=True)
class LlmConfig:
    provider: ProviderName = "mock"
    model: str = ""
    concurrency: int = 4


@dataclass(frozen=True)
class PreprocessConfig:
    text_strategy: Literal["direct", "llm"] = "direct"
    max_file_mb: int = 50


@dataclass(frozen=True)
class WikiConfig:
    tag_prefix: str = ""
    page_dir: Path = Path("")


@dataclass(frozen=True)
class AppConfig:
    paths: PathConfig = field(default_factory=PathConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    wiki: WikiConfig = field(default_factory=WikiConfig)
    mime_overrides: dict[str, str] = field(default_factory=dict)


def load_config(config_path: Path | str = "wiki.config.toml") -> AppConfig:
    load_dotenv()
    path = Path(config_path)
    data: dict = {}
    if path.exists():
        data = tomllib.loads(path.read_text(encoding="utf-8"))

    paths_data = data.get("paths", {})
    llm_data = data.get("llm", {})
    preprocess_data = data.get("preprocess", {})
    wiki_data = data.get("wiki", {})

    provider = os.getenv("LLM_WIKI_PROVIDER", llm_data.get("provider", "mock"))
    
    # Prioritize provider-specific model env vars, then general LLM_WIKI_MODEL, then config.
    model = os.getenv("LLM_WIKI_MODEL")
    if not model:
        if provider == "openai":
            model = os.getenv("OPENAI_MODEL")
        elif provider == "vertex":
            model = os.getenv("VERTEX_MODEL")
        elif provider == "azure_openai":
            model = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    if not model:
        model = llm_data.get("model", "")

    return AppConfig(
        paths=PathConfig(
            raw=Path(paths_data.get("raw", "raw")),
            preprocessed=Path(paths_data.get("preprocessed", "preprocessed")),
            vault=Path(paths_data.get("vault", "vault")),
            build=Path(paths_data.get("build", ".wiki_build")),
        ),
        llm=LlmConfig(
            provider=_as_provider(provider),
            model=model,
            concurrency=int(llm_data.get("concurrency", 4)),
        ),
        preprocess=PreprocessConfig(
            text_strategy=preprocess_data.get("text_strategy", "direct"),
            max_file_mb=int(preprocess_data.get("max_file_mb", 50)),
        ),
        wiki=WikiConfig(
            tag_prefix=wiki_data.get("tag_prefix", ""),
            page_dir=Path(wiki_data.get("page_dir", "")),
        ),
        mime_overrides=dict(data.get("mime_overrides", {})),
    )


def _as_provider(value: str) -> ProviderName:
    if value not in {"mock", "openai", "azure_openai", "vertex"}:
        raise ValueError(f"Unsupported provider: {value}")
    return value  # type: ignore[return-value]

