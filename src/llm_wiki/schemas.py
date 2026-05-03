from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryResult(BaseModel):
    summary: str
    key_terms: list[str] = Field(default_factory=list)


class ConceptPage(BaseModel):
    title: str
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    concept_type: str = "concept"
    confidence: float = 0.0
    body: str


class ConceptPagesResult(BaseModel):
    pages: list[ConceptPage] = Field(default_factory=list)


class DuplicateMatch(BaseModel):
    title: str
    is_identical: bool
    reason: str


class MergeGroupDecision(BaseModel):
    matches: list[DuplicateMatch]

