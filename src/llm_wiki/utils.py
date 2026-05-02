from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_relative(path: Path, root: Path) -> Path:
    return path.resolve().relative_to(root.resolve())


def markdown_with_frontmatter(frontmatter: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{yaml_text}\n---\n\n{body.strip()}\n"


def split_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return {}, markdown
    meta = yaml.safe_load(markdown[4:end]) or {}
    body = markdown[end + 5 :].lstrip()
    return meta, body


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[\s/]+", "-", lowered)
    lowered = re.sub(r"[^0-9a-zA-Z가-힣._-]+", "", lowered)
    return lowered.strip("-") or "untitled"


def normalize_tag(value: str, prefix: str = "") -> str:
    tag = re.sub(r"\s+", "-", value.strip().lower())
    tag = re.sub(r"[^0-9a-zA-Z가-힣/_-]+", "", tag).strip("/-")
    if prefix:
        tag = f"{prefix.strip('/')}/{tag}"
    return tag

