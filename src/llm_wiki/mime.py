from __future__ import annotations

import mimetypes
from pathlib import Path

TEXT_MIME_PREFIXES = ("text/",)
TEXT_MIME_TYPES = {
    "application/json",
    "application/x-yaml",
    "application/xml",
}

OPENAI_FILE_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}

AZURE_OPENAI_FILE_MIME_TYPES = set(OPENAI_FILE_MIME_TYPES)

VERTEX_FILE_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/heic",
    "image/heif",
    "text/plain",
    "text/markdown",
}


def detect_mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    if path.suffix.lower() in {".md", ".markdown"}:
        return "text/markdown"
    if path.suffix.lower() in {".yaml", ".yml"}:
        return "application/x-yaml"
    return "application/octet-stream"


def is_text_mime(mime_type: str) -> bool:
    return mime_type.startswith(TEXT_MIME_PREFIXES) or mime_type in TEXT_MIME_TYPES


def default_supported_mimes(provider: str) -> set[str]:
    if provider == "openai":
        return set(OPENAI_FILE_MIME_TYPES)
    if provider == "azure_openai":
        return set(AZURE_OPENAI_FILE_MIME_TYPES)
    if provider == "vertex":
        return set(VERTEX_FILE_MIME_TYPES)
    if provider == "mock":
        return set(OPENAI_FILE_MIME_TYPES)
    return set()

