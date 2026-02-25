"""Pydantic models for the query pipeline's structured LLM responses."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


def _coerce_str(v: object) -> str:
    return str(v) if not isinstance(v, str) else v


class SourceReference(BaseModel):
    path: str
    title: str
    relevance: Annotated[str, BeforeValidator(_coerce_str)]


class DocumentSelection(BaseModel):
    reasoning: str
    selected_paths: list[str]


class QueryAnswer(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
