"""Pydantic models for the query pipeline's structured LLM responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    path: str
    title: str
    relevance: str


class DocumentSelection(BaseModel):
    reasoning: str
    selected_paths: list[str]


class QueryAnswer(BaseModel):
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
