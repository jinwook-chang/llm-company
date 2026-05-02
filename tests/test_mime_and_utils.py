from __future__ import annotations

from llm_wiki.providers import OpenAIProvider
from llm_wiki.utils import normalize_tag, slugify


def test_provider_mime_override() -> None:
    provider = OpenAIProvider(mime_overrides={"application/vnd.ms-excel": "llm", "application/pdf": "docling"})

    assert provider.supports_mime("application/vnd.ms-excel") is True
    assert provider.supports_mime("application/pdf") is False


def test_slugify_and_tags() -> None:
    assert slugify("A Concept / 정책") == "a-concept-정책"
    assert normalize_tag("Internal Wiki", "company") == "company/internal-wiki"
