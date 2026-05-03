from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from llm_wiki.mime import default_supported_mimes

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class MarkdownResult:
    markdown: str
    processor: str


class LlmProvider:
    name = "base"

    def __init__(self, model: str = "", mime_overrides: dict[str, str] | None = None):
        self.model = model
        self.mime_overrides = mime_overrides or {}

    def supports_mime(self, mime_type: str) -> bool:
        override = self.mime_overrides.get(mime_type)
        if override == "llm":
            return True
        if override == "docling":
            return False
        return mime_type in default_supported_mimes(self.name)

    def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
        raise NotImplementedError

    def generate_structured(self, system_prompt: str, messages: list[dict[str, str]], response_schema: type[T]) -> T:
        raise NotImplementedError


class MockProvider(LlmProvider):
    name = "mock"

    def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
        return MarkdownResult(
            markdown=f"# Extracted: {path.stem}\n\nMock Markdown extracted from `{path.name}` ({mime_type}).",
            processor="llm:mock",
        )

    def generate_structured(self, system_prompt: str, messages: list[dict[str, str]], response_schema: type[T]) -> T:
        schema_name = response_schema.__name__
        joined = "\n\n".join(message["content"] for message in messages)
        title = _first_heading_or_title(joined)

        if schema_name == "SummaryResult":
            return response_schema.model_validate({"summary": f"Mock summary for {title}", "key_terms": [title]})
        if schema_name == "ConceptPagesResult":
            return response_schema.model_validate(
                {
                    "pages": [
                        {
                            "title": title,
                            "aliases": [],
                            "tags": ["mock", "internal-wiki"],
                            "concept_type": "concept",
                            "confidence": 0.5,
                            "body": f"# {title}\n\n{_truncate(joined, 800)}",
                        }
                    ]
                }
            )
        if schema_name == "ConceptPage":
            refined_title = _canonical_seed_title(joined) or title
            return response_schema.model_validate(
                {
                    "title": refined_title,
                    "aliases": [],
                    "tags": ["mock", "refined"],
                    "concept_type": "concept",
                    "confidence": 0.5,
                    "body": f"# {title}\n\nMock refined page.\n\n{_truncate(joined, 800)}",
                }
            )
        raise ValueError(f"MockProvider does not know schema {schema_name}")


class OpenAIProvider(LlmProvider):
    name = "openai"

    def _client(self) -> Any:
        from openai import OpenAI

        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
        client = self._client()
        content = [
            {"type": "input_text", "text": prompt},
            {
                "type": "input_file",
                "filename": path.name,
                "file_data": f"data:{mime_type};base64,{_b64(path)}",
            },
        ]
        response = client.responses.create(
            model=self.model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            input=[{"role": "user", "content": content}],
        )
        return MarkdownResult(markdown=response.output_text, processor="llm:openai")

    def generate_structured(self, system_prompt: str, messages: list[dict[str, str]], response_schema: type[T]) -> T:
        client = self._client()
        response = client.responses.parse(
            model=self.model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            instructions=system_prompt,
            input=messages,
            text_format=response_schema,
        )
        return response.output_parsed


class AzureOpenAIProvider(OpenAIProvider):
    name = "azure_openai"

    def _client(self) -> Any:
        from openai import AzureOpenAI

        return AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
        result = super().extract_markdown_from_file(path, mime_type, prompt)
        return MarkdownResult(result.markdown, "llm:azure_openai")


class VertexProvider(LlmProvider):
    name = "vertex"

    def _client(self) -> Any:
        from google import genai

        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for the vertex provider.")
        return genai.Client(vertexai=True, project=project, location=location)

    def extract_markdown_from_file(self, path: Path, mime_type: str, prompt: str) -> MarkdownResult:
        from google.genai import types

        client = self._client()
        part = types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type)
        response = client.models.generate_content(
            model=self.model or os.getenv("VERTEX_MODEL", "gemini-2.5-pro"),
            contents=[prompt, part],
        )
        return MarkdownResult(markdown=response.text or "", processor="llm:vertex")

    def generate_structured(self, system_prompt: str, messages: list[dict[str, str]], response_schema: type[T]) -> T:
        client = self._client()
        prompt = system_prompt + "\n\n" + "\n\n".join(m["content"] for m in messages)
        response = client.models.generate_content(
            model=self.model or os.getenv("VERTEX_MODEL", "gemini-2.5-pro"),
            contents=prompt,
            config={"response_mime_type": "application/json", "response_schema": response_schema},
        )
        data = json.loads(response.text or "{}")
        return response_schema.model_validate(data)


def make_provider(name: str, model: str = "", mime_overrides: dict[str, str] | None = None) -> LlmProvider:
    if name == "mock":
        return MockProvider(model, mime_overrides)
    if name == "openai":
        return OpenAIProvider(model, mime_overrides)
    if name == "azure_openai":
        return AzureOpenAIProvider(model or os.getenv("AZURE_OPENAI_DEPLOYMENT", ""), mime_overrides)
    if name == "vertex":
        return VertexProvider(model, mime_overrides)
    raise ValueError(f"Unsupported provider: {name}")


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _first_heading_or_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "Untitled"
        if stripped:
            return stripped[:80]
    return "Untitled"


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def _canonical_seed_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("Canonical seed title:"):
            return line.split(":", 1)[1].strip()
    return ""
